@echo off
REM Android App Build Script
REM Builds the Android APK for Mobile GCS

echo ================================
echo Android App Build Script
echo ================================
echo.

cd /d "%~dp0..\monitoring\mobile_app_android"

REM Check if gradlew exists
if not exist "gradlew.bat" (
    echo [ERROR] gradlew.bat not found!
    echo.
    echo Please open this project in Android Studio first to initialize Gradle.
    echo Or run: gradle wrapper
    pause
    exit /b 1
)

echo [STEP 1] Cleaning previous build...
call gradlew.bat clean
if errorlevel 1 (
    echo [ERROR] Clean failed
    pause
    exit /b 1
)

echo.
echo [STEP 2] Building Debug APK...
call gradlew.bat assembleDebug
if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ================================
echo Build Complete!
echo ================================
echo.
echo APK location:
echo   app\build\outputs\apk\debug\app-debug.apk
echo.
echo Next steps:
echo 1. Transfer APK to your Android device
echo 2. Install the APK
echo 3. Configure server IP in the app (ApiClient.kt)
echo.
pause
