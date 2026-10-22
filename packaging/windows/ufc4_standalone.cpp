#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <shlwapi.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <wrl.h>
#include <wrl/client.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

#include "build/native/include/WebView2.h"

using namespace Microsoft::WRL;

#define PATHW (MAX_PATH * 4)

static wchar_t root[PATHW];
static wchar_t python_exe[PATHW];
static PROCESS_INFORMATION pi_server = { 0 };
static HWND g_hWnd = NULL;
static ComPtr<ICoreWebView2Controller> g_controller;
static ComPtr<ICoreWebView2> g_webview;
static int g_port = 44209;

typedef HRESULT (STDAPICALLTYPE *CreateCoreWebView2EnvironmentWithOptionsFn)(
    PCWSTR browserExecutableFolder,
    PCWSTR userDataFolder,
    ICoreWebView2EnvironmentOptions* environmentOptions,
    ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler* environment_created_handler
);

static int exists(const wchar_t *path) {
    return GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES;
}

static void join(wchar_t *out_path, size_t n, const wchar_t *a, const wchar_t *b) {
    _snwprintf(out_path, n, L"%ls\\%ls", a, b);
    out_path[n - 1] = 0;
}

static int find_python(wchar_t *out_path) {
    wchar_t local_py[PATHW];
    join(local_py, PATHW, root, L"python\\python.exe");
    if (exists(local_py)) {
        wcsncpy(out_path, local_py, PATHW - 1);
        return 1;
    }

    wchar_t path_py[PATHW];
    if (SearchPathW(NULL, L"python.exe", NULL, PATHW, path_py, NULL)) {
        wcsncpy(out_path, path_py, PATHW - 1);
        return 1;
    }

    wchar_t user_prof[PATHW];
    if (GetEnvironmentVariableW(L"USERPROFILE", user_prof, PATHW)) {
        const wchar_t *py_dirs[] = {
            L"AppData\\Local\\Programs\\Python\\Python314\\python.exe",
            L"AppData\\Local\\Programs\\Python\\Python313\\python.exe",
            L"AppData\\Local\\Programs\\Python\\Python312\\python.exe",
            L"AppData\\Local\\Programs\\Python\\Python311\\python.exe",
            L"AppData\\Local\\Programs\\Python\\Python310\\python.exe",
            L"AppData\\Local\\Microsoft\\WindowsApps\\python.exe",
            L"AppData\\Local\\Python\\bin\\python.exe"
        };
        for (int i = 0; i < (int)(sizeof(py_dirs) / sizeof(py_dirs[0])); ++i) {
            join(path_py, PATHW, user_prof, py_dirs[i]);
            if (exists(path_py)) {
                wcsncpy(out_path, path_py, PATHW - 1);
                return 1;
            }
        }
    }

    return 0;
}

static int wait_for_server(int port, int max_ms) {
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return 0;

    int success = 0;
    int elapsed = 0;
    while (elapsed < max_ms) {
        SOCKET s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (s != INVALID_SOCKET) {
            sockaddr_in addr;
            addr.sin_family = AF_INET;
            addr.sin_port = htons((u_short)port);
            addr.sin_addr.s_addr = inet_addr("127.0.0.1");

            // Non-blocking connect or short timeout
            DWORD timeout = 200;
            setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, (const char*)&timeout, sizeof(timeout));
            setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, (const char*)&timeout, sizeof(timeout));

            if (connect(s, (sockaddr*)&addr, sizeof(addr)) == 0) {
                success = 1;
                closesocket(s);
                break;
            }
            closesocket(s);
        }
        Sleep(50);
        elapsed += 50;
    }

    WSACleanup();
    return success;
}

static void resize_webview() {
    if (g_controller && g_hWnd) {
        RECT bounds;
        GetClientRect(g_hWnd, &bounds);
        g_controller->put_Bounds(bounds);
    }
}

static LRESULT CALLBACK WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_SIZE:
            resize_webview();
            return 0;

        case WM_CLOSE:
            DestroyWindow(hWnd);
            return 0;

        case WM_DESTROY:
            if (pi_server.hProcess) {
                TerminateProcess(pi_server.hProcess, 0);
                CloseHandle(pi_server.hProcess);
                CloseHandle(pi_server.hThread);
                pi_server.hProcess = NULL;
            }
            PostQuitMessage(0);
            return 0;
    }
    return DefWindowProcW(hWnd, msg, wParam, lParam);
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR lpCmdLine, int nCmdShow) {
    (void)hPrevInstance; (void)lpCmdLine;

    // Enable High-DPI
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);

    GetModuleFileNameW(NULL, root, PATHW);
    wchar_t *slash = wcsrchr(root, L'\\');
    if (slash) *slash = 0;
    SetCurrentDirectoryW(root);

    if (!find_python(python_exe)) {
        MessageBoxW(NULL,
            L"Python 3.10+ is required to launch EA SPORTS UFC 4.\nPlease ensure python is installed.",
            L"EA SPORTS UFC 4", MB_ICONERROR | MB_OK);
        return 1;
    }

    // Clean old port file
    wchar_t port_file[PATHW];
    join(port_file, PATHW, root, L"user\\launcher_port.txt");
    DeleteFileW(port_file);

    // Launch background server
    wchar_t server_script[PATHW];
    join(server_script, PATHW, root, L"scripts\\launcher_server.py");

    wchar_t py_cmd[PATHW * 2];
    _snwprintf(py_cmd, PATHW * 2, L"\"%ls\" -u \"%ls\"", python_exe, server_script);

    STARTUPINFOW si_server = { .cb = sizeof(si_server) };
    if (!CreateProcessW(NULL, py_cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, root, &si_server, &pi_server)) {
        MessageBoxW(NULL, L"Failed to start launcher backend server.", L"Error", MB_ICONERROR | MB_OK);
        return 1;
    }

    // Read port
    int port = 44209;
    for (int i = 0; i < 60; ++i) {
        Sleep(50);
        FILE *f = _wfopen(port_file, L"r");
        if (f) {
            if (fwscanf(f, L"%d", &port) == 1 && port > 0) {
                fclose(f);
                break;
            }
            fclose(f);
        }
    }
    g_port = port;

    // Wait until server is ACTUALLY accepting connections (prevents ERR_CONNECTION_REFUSED)
    wait_for_server(g_port, 4000);

    // Register Win32 Window Class
    WNDCLASSEXW wcex = { sizeof(WNDCLASSEXW) };
    wcex.style = CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc = WndProc;
    wcex.hInstance = hInstance;
    wcex.hIcon = LoadIconW(hInstance, MAKEINTRESOURCEW(1));
    wcex.hIconSm = LoadIconW(hInstance, MAKEINTRESOURCEW(1));
    wcex.hCursor = LoadCursorW(NULL, IDC_ARROW);
    wcex.hbrBackground = CreateSolidBrush(RGB(7, 9, 14)); // Dark match with UFC 4 theme
    wcex.lpszClassName = L"UFC4_STANDALONE_LAUNCHER";

    RegisterClassExW(&wcex);

    // Compute window size & center position
    int w = 1220;
    int h = 840;
    int screenW = GetSystemMetrics(SM_CXSCREEN);
    int screenH = GetSystemMetrics(SM_CYSCREEN);
    int posX = (screenW > w) ? (screenW - w) / 2 : 50;
    int posY = (screenH > h) ? (screenH - h) / 2 : 50;

    g_hWnd = CreateWindowExW(
        0,
        L"UFC4_STANDALONE_LAUNCHER",
        L"EA SPORTS\x2122 UFC\x00AE 4 \x2014 Windows Native Port",
        WS_OVERLAPPEDWINDOW,
        posX, posY, w, h,
        NULL, NULL, hInstance, NULL
    );

    if (!g_hWnd) {
        return 1;
    }

    ShowWindow(g_hWnd, nCmdShow);
    UpdateWindow(g_hWnd);

    // Load WebView2Loader.dll
    wchar_t loader_path[PATHW];
    join(loader_path, PATHW, root, L"WebView2Loader.dll");
    HMODULE hLoader = LoadLibraryW(loader_path);
    if (!hLoader) {
        hLoader = LoadLibraryW(L"WebView2Loader.dll");
    }

    if (!hLoader) {
        // Fallback: search in deps
        join(loader_path, PATHW, L"E:\\recompile\\deps\\build\\native\\x64", L"WebView2Loader.dll");
        hLoader = LoadLibraryW(loader_path);
    }

    CreateCoreWebView2EnvironmentWithOptionsFn createEnv = NULL;
    if (hLoader) {
        createEnv = (CreateCoreWebView2EnvironmentWithOptionsFn)GetProcAddress(hLoader, "CreateCoreWebView2EnvironmentWithOptions");
    }

    if (!createEnv) {
        // Fallback: launch Edge in chromeless app mode
        wchar_t edge_path[PATHW] = L"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
        wchar_t profile_dir[PATHW];
        join(profile_dir, PATHW, root, L"user\\browser_profile");

        wchar_t browser_cmd[PATHW * 3];
        _snwprintf(browser_cmd, PATHW * 3,
            L"\"%ls\" --app=http://127.0.0.1:%d --window-size=1220,840 --user-data-dir=\"%ls\" --no-first-run --no-default-browser-check --disable-features=Translate,OptimizationHints,MediaRouter --disable-extensions",
            edge_path, g_port, profile_dir);

        STARTUPINFOW si_b = { .cb = sizeof(si_b) };
        PROCESS_INFORMATION pi_b = { 0 };
        if (CreateProcessW(NULL, browser_cmd, NULL, NULL, FALSE, 0, NULL, root, &si_b, &pi_b)) {
            DestroyWindow(g_hWnd);
            WaitForSingleObject(pi_b.hProcess, INFINITE);
            CloseHandle(pi_b.hProcess);
            CloseHandle(pi_b.hThread);
            if (pi_server.hProcess) {
                TerminateProcess(pi_server.hProcess, 0);
            }
            return 0;
        }

        MessageBoxW(NULL, L"Failed to initialize native WebView2 control.", L"Error", MB_ICONERROR | MB_OK);
        return 1;
    }

    // User data directory strictly on Drive E:
    wchar_t webview_data[PATHW];
    join(webview_data, PATHW, root, L"user\\webview2_data");

    // Initialize Native WebView2
    HRESULT hr = createEnv(
        NULL,
        webview_data,
        NULL,
        Callback<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler>(
            [hInstance](HRESULT result, ICoreWebView2Environment* env) -> HRESULT {
                if (FAILED(result) || !env) {
                    MessageBoxW(g_hWnd, L"Failed to create WebView2 environment.", L"Error", MB_ICONERROR | MB_OK);
                    return result;
                }

                env->CreateCoreWebView2Controller(
                    g_hWnd,
                    Callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler>(
                        [](HRESULT res2, ICoreWebView2Controller* controller) -> HRESULT {
                            if (FAILED(res2) || !controller) {
                                MessageBoxW(g_hWnd, L"Failed to create WebView2 controller.", L"Error", MB_ICONERROR | MB_OK);
                                return res2;
                            }

                            g_controller = controller;
                            g_controller->put_IsVisible(TRUE);
                            resize_webview();

                            g_controller->get_CoreWebView2(&g_webview);
                            if (g_webview) {
                                ComPtr<ICoreWebView2Settings> settings;
                                g_webview->get_Settings(&settings);
                                if (settings) {
                                    settings->put_AreDevToolsEnabled(FALSE);
                                    settings->put_AreDefaultContextMenusEnabled(FALSE);
                                    settings->put_IsStatusBarEnabled(FALSE);
                                }

                                wchar_t url[256];
                                _snwprintf(url, 256, L"http://127.0.0.1:%d", g_port);
                                g_webview->Navigate(url);
                            }
                            return S_OK;
                        }
                    ).Get()
                );
                return S_OK;
            }
        ).Get()
    );

    if (FAILED(hr)) {
        MessageBoxW(NULL, L"WebView2 initialization request failed.", L"Error", MB_ICONERROR | MB_OK);
        return 1;
    }

    // Message Loop
    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    return (int)msg.wParam;
}
