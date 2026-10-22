#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <shlwapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

#define PATHW (MAX_PATH * 4)

static wchar_t root[PATHW];
static wchar_t python_exe[PATHW];
static wchar_t browser_exe[PATHW];

static int exists(const wchar_t *path) {
    return GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES;
}

static void join(wchar_t *out_path, size_t n, const wchar_t *a, const wchar_t *b) {
    _snwprintf(out_path, n, L"%ls\\%ls", a, b);
    out_path[n - 1] = 0;
}

static int find_python(wchar_t *out_path) {
    // 1. Check local python
    wchar_t local_py[PATHW];
    join(local_py, PATHW, root, L"python\\python.exe");
    if (exists(local_py)) {
        wcsncpy(out_path, local_py, PATHW - 1);
        return 1;
    }

    // 2. Search in PATH via SearchPathW
    wchar_t path_py[PATHW];
    if (SearchPathW(NULL, L"python.exe", NULL, PATHW, path_py, NULL)) {
        wcsncpy(out_path, path_py, PATHW - 1);
        return 1;
    }

    // 3. Check AppData Local Programs Python
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

static int find_browser(wchar_t *out_path) {
    const wchar_t *candidates[] = {
        L"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        L"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
        L"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        L"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
    };

    for (int i = 0; i < (int)(sizeof(candidates) / sizeof(candidates[0])); ++i) {
        if (exists(candidates[i])) {
            wcsncpy(out_path, candidates[i], PATHW - 1);
            return 1;
        }
    }

    // Fallback: search in PATH
    if (SearchPathW(NULL, L"msedge.exe", NULL, PATHW, out_path, NULL)) return 1;
    if (SearchPathW(NULL, L"chrome.exe", NULL, PATHW, out_path, NULL)) return 1;

    return 0;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR cmdline, int show) {
    (void)instance; (void)previous; (void)cmdline; (void)show;

    GetModuleFileNameW(NULL, root, PATHW);
    wchar_t *slash = wcsrchr(root, L'\\');
    if (slash) *slash = 0;
    SetCurrentDirectoryW(root);

    if (!find_python(python_exe)) {
        MessageBoxW(NULL,
            L"Python 3 is required to launch the game configuration.\nPlease install Python 3 or ensure python.exe is available in your PATH.",
            L"EA SPORTS UFC 4 Launcher",
            MB_ICONERROR | MB_OK);
        return 1;
    }

    if (!find_browser(browser_exe)) {
        MessageBoxW(NULL,
            L"Microsoft Edge or Google Chrome is required to display the modern launcher UI.",
            L"EA SPORTS UFC 4 Launcher",
            MB_ICONERROR | MB_OK);
        return 1;
    }

    // Clear old port file
    wchar_t port_file[PATHW];
    join(port_file, PATHW, root, L"user\\launcher_port.txt");
    DeleteFileW(port_file);

    // Start background Python launcher server
    wchar_t server_script[PATHW];
    join(server_script, PATHW, root, L"scripts\\launcher_server.py");

    wchar_t py_cmd[PATHW * 2];
    _snwprintf(py_cmd, PATHW * 2, L"\"%ls\" -u \"%ls\"", python_exe, server_script);

    STARTUPINFOW si_server = { .cb = sizeof(si_server) };
    PROCESS_INFORMATION pi_server = { 0 };

    if (!CreateProcessW(NULL, py_cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, root, &si_server, &pi_server)) {
        MessageBoxW(NULL, L"Failed to start launcher backend server.", L"Error", MB_ICONERROR | MB_OK);
        return 1;
    }

    // Wait up to 6 seconds for server to start and write port
    int port = 0;
    for (int i = 0; i < 60; ++i) {
        Sleep(100);
        FILE *f = _wfopen(port_file, L"r");
        if (f) {
            if (fwscanf(f, L"%d", &port) == 1 && port > 0) {
                fclose(f);
                break;
            }
            fclose(f);
        }
    }

    if (port <= 0) {
        TerminateProcess(pi_server.hProcess, 1);
        CloseHandle(pi_server.hProcess);
        CloseHandle(pi_server.hThread);
        MessageBoxW(NULL, L"Launcher server timed out while initializing.", L"Error", MB_ICONERROR | MB_OK);
        return 1;
    }

    // Browser profile directory strictly on Drive E:
    wchar_t profile_dir[PATHW];
    join(profile_dir, PATHW, root, L"user\\browser_profile");

    // Launch standalone Edge / Chrome in app mode
    wchar_t browser_cmd[PATHW * 3];
    _snwprintf(browser_cmd, PATHW * 3,
        L"\"%ls\" --app=\"http://127.0.0.1:%d\" --window-size=1200,820 --user-data-dir=\"%ls\" --no-first-run --no-default-browser-check",
        browser_exe, port, profile_dir);

    STARTUPINFOW si_browser = { .cb = sizeof(si_browser) };
    PROCESS_INFORMATION pi_browser = { 0 };

    if (CreateProcessW(NULL, browser_cmd, NULL, NULL, FALSE, 0, NULL, root, &si_browser, &pi_browser)) {
        // Wait until user closes the launcher app window
        WaitForSingleObject(pi_browser.hProcess, INFINITE);
        CloseHandle(pi_browser.hProcess);
        CloseHandle(pi_browser.hThread);
    } else {
        MessageBoxW(NULL, L"Failed to launch browser interface.", L"Error", MB_ICONERROR | MB_OK);
    }

    // Clean up background server
    TerminateProcess(pi_server.hProcess, 0);
    CloseHandle(pi_server.hProcess);
    CloseHandle(pi_server.hThread);

    return 0;
}
