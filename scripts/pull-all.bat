@echo off
setlocal enabledelayedexpansion

REM Pull all repos under C:\github. Edit REPOS list to add/remove.

set "ROOT=C:\github"
set REPOS=^
 ArborView ^
 BOPPER ^
 BorgRWProblems ^
 CVEN5393 ^
 FlowDetection ^
 ParetoExplorer ^
 block-doku-trivia ^
 cross-country-courier ^
 crypts-of-the-shifting-code ^
 ensemble-viewer ^
 hardball-trivia ^
 lifelogue ^
 parasol-es ^
 parasolpy ^
 pitch-perfect-roguelike ^
 promptukit ^
 survival-kit

set /a OK=0
set /a FAIL=0
set "FAILED="

for %%R in (%REPOS%) do (
    echo.
    echo === %%R ===
    if not exist "%ROOT%\%%R\.git" (
        echo   SKIP: not a git repo
        set /a FAIL+=1
        set "FAILED=!FAILED! %%R"
    ) else (
        pushd "%ROOT%\%%R"
        git pull --ff-only
        if errorlevel 1 (
            set /a FAIL+=1
            set "FAILED=!FAILED! %%R"
        ) else (
            set /a OK+=1
        )
        popd
    )
)

echo.
echo ============================
echo  OK:     %OK%
echo  FAILED: %FAIL%
if defined FAILED echo  Failed repos:%FAILED%
echo ============================
pause
endlocal
