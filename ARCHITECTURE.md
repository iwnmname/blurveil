# Архитектура Blurveil

```mermaid
flowchart TD
    User[Пользователь] --> Hotkey[Глобальная горячая клавиша<br/>Ctrl+Alt/Option+S]
    User --> TrayMenu[Меню в трее]

    Hotkey --> TrayApp[gui.tray<br/>BlurveilTrayApp]
    TrayMenu --> TrayApp

    TrayApp --> CaptureChoice{Режим захвата}
    CaptureChoice --> Snipper[gui.snipper<br/>SnippingWidget]
    CaptureChoice --> Fullscreen[platforms.screen_capture<br/>grab_virtual_desktop]

    Snipper --> ScreenCapture[platforms.screen_capture<br/>ScreenCapture]
    Fullscreen --> ScreenCapture

    ScreenCapture --> Worker[gui.analysis<br/>ImageAnalysisWorker]
    Worker --> Sanitizer[core.sanitizer<br/>конвертация Qt/OpenCV]
    Sanitizer --> Analyzer[core.analyzer<br/>OCR + правила поиска секретов]

    Analyzer --> OCR[Tesseract OCR]
    Analyzer --> ObjectDetectors[core.detectors<br/>QR-коды и лица]
    Analyzer --> Regions[core.regions<br/>утилиты для областей]

    OCR --> AnalysisResult[Результат анализа<br/>cv_image + ocr_boxes + auto_regions]
    ObjectDetectors --> AnalysisResult
    Regions --> AnalysisResult

    AnalysisResult --> Preview[gui.preview<br/>PreviewWindow + ImageCanvas]
    Preview --> ManualEdit[Ручная правка блюра<br/>включить, добавить, удалить]
    Preview --> Crop[Обрезка]
    Preview --> Export{Экспорт}

    Export --> Clipboard[Скопировать в буфер]
    Export --> File[Сохранить PNG/JPEG]
```

## Карта модулей

```mermaid
flowchart LR
    subgraph App["Точка входа"]
        Main[main.py]
    end

    subgraph GUI["gui"]
        Tray[tray.py<br/>координатор приложения]
        Snip[snipper.py<br/>оверлей выделения экрана]
        AnalysisUI[analysis.py<br/>фоновый worker и окно ожидания]
        Preview[preview.py<br/>предпросмотр, блюр, обрезка, экспорт]
        Hotkey[hotkey.py<br/>глобальная hotkey через pynput]
        PermissionsUI[permissions.py<br/>диалог разрешений macOS]
        Errors[errors.py<br/>безопасная обработка ошибок Qt]
    end

    subgraph Core["core"]
        Analyzer[analyzer.py<br/>OCR и поиск чувствительных данных]
        Sanitizer[sanitizer.py<br/>конвертация, блюр, сохранение]
        Regions[regions.py<br/>операции с прямоугольниками]
        Detectors[detectors<br/>детекторы QR-кодов и лиц]
    end

    subgraph Platforms["platforms"]
        ScreenCapture[screen_capture.py<br/>захват через mss / macOS Retina]
        MacPerms[macos_permissions.py<br/>проверка Screen Recording и Accessibility]
    end

    Main --> Tray
    Tray --> Hotkey
    Tray --> Snip
    Tray --> AnalysisUI
    Tray --> Preview
    Tray --> PermissionsUI
    Tray --> ScreenCapture

    Snip --> ScreenCapture
    AnalysisUI --> Sanitizer
    Preview --> Sanitizer
    PermissionsUI --> MacPerms
    Errors --> Tray

    Sanitizer --> Analyzer
    Analyzer --> Detectors
    Analyzer --> Regions
    Detectors --> Regions
```

## Ответственность частей

| Часть | За что отвечает |
| --- | --- |
| `main.py` | Проверка платформы и запуск Qt-приложения. |
| `gui` | Пользовательский сценарий: трей, hotkey, выделение экрана, фоновая обработка, предпросмотр, экспорт, ошибки. |
| `core` | Анализ и обработка изображения: OCR, поиск чувствительных данных, детекторы объектов, рендер блюра. |
| `platforms` | Системно-зависимый захват экрана и проверка разрешений. |
