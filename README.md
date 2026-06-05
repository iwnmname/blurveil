<p align="center">
  <img src="assets/icons/blurveil-icon-1024.png" alt="Blurveil" width="128" height="128">
</p>

<h1 align="center">Blurveil</h1>

<p align="center">
  <strong>Безопасные скриншоты с автоматическим блюром конфиденциальных данных.</strong>
</p>

<p align="center">
  <a href="https://github.com/iwnmname/blurveil/actions/workflows/ci.yml">
    <img alt="CI" src="https://github.com/iwnmname/blurveil/actions/workflows/ci.yml/badge.svg?branch=main">
  </a>
  <a href="https://github.com/iwnmname/blurveil/actions/workflows/release.yml">
    <img alt="Release build" src="https://github.com/iwnmname/blurveil/actions/workflows/release.yml/badge.svg">
  </a>
  <a href="https://github.com/iwnmname/blurveil/releases">
    <img alt="Latest release" src="https://img.shields.io/github/v/release/iwnmname/blurveil?sort=semver">
  </a>
  <a href="https://github.com/iwnmname/blurveil/releases">
    <img alt="Downloads" src="https://img.shields.io/github/downloads/iwnmname/blurveil/total">
  </a>
  <a href="LICENSE">
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-purple.svg">
  </a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-blue">
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-555">
  <img alt="Local processing" src="https://img.shields.io/badge/processing-local-2ea44f">
</p>

Простой инструмент для автоматического сканирования и замазывания конфиденциальных данных на скриншотах. Достаточно нажать сочетание клавиш, чтобы сделать безопасный скрин, готовый для публикации или отправки.

---

## Проблема

Люди часто делятся скриншотами, которые могут содержать личные данные: пароли, контакты, адреса. Это создаёт риск утечки конфиденциальной информации, а ручное редактирование отнимает время и может быть неточным.

## Решение

Blurveil встраивается прямо в жест «сделать скрин» и автоматически блюрит ключи, пароли, адреса — без отдельного редактора и без сети.

Большинство инструментов умеют только рисовать прямоугольники вручную. Онлайн-редакторы могут хранить загруженное изображение. Blurveil работает локально и автоматически.

---

## Возможности

- Захват произвольной области экрана горячей клавишей `Ctrl+Option+S` на macOS или `Ctrl+Alt+S` на Windows
- Автоматическое OCR-распознавание текста на скриншоте
- Детектирование конфиденциальных данных: email-адреса, IP-адреса, пароли и секретные ключи
- Автоматическое обнаружение и блюр QR-кодов
- Gaussian-блюр поверх найденных регионов
- Окно предпросмотра с возможностью скопировать результат в буфер обмена или сохранить в файл
- Иконка в системном трее для быстрого доступа
- Полностью локальная обработка — данные никуда не отправляются

---

## Поддерживаемые платформы

Blurveil сейчас поддерживает macOS и Windows.

Linux/Ubuntu не поддерживается: приложение завершится с понятным сообщением при запуске на Linux.

---

## Установка

**Требования:** macOS или Windows, Python 3.12+, Tesseract OCR

```bash
# Клонировать репозиторий
git clone https://github.com/iwnmname/blurveil.git
cd blurveil

# Установить зависимости (через uv)
uv sync

# Или через pip
pip install -e .
```

## Запуск

```bash
uv run python main.py
```

После запуска приложение появится в системном трее. Нажмите `Ctrl+Option+S` на macOS или `Ctrl+Alt+S` на Windows, выделите область экрана и получите обработанный скриншот.

При обработке больших скриншотов появится небольшое окно ожидания: OCR и поиск конфиденциальных данных выполняются в фоне, поэтому интерфейс не должен зависать.

## Разрешения macOS

При первом запуске Blurveil проверит нужные разрешения macOS и покажет окно с подсказками, если чего-то не хватает.

Включите для приложения:

- **Запись экрана** — нужна для захвата скриншотов
- **Универсальный доступ** — нужен для стабильной работы глобальной горячей клавиши
- **Мониторинг ввода** — нужен, если macOS не передаёт глобальную горячую клавишу

Проверку можно открыть вручную из меню в системном трее: **Проверить разрешения macOS**.

## Тесты

```bash
uv run python -m unittest discover -v
```

---

## Стек технологий

| Компонент | Технология |
|---|---|
| GUI и трей | PyQt6 |
| Захват экрана | mss |
| OCR | Tesseract / pytesseract |
| Обработка изображений | OpenCV, Pillow |
| Глобальные горячие клавиши | pynput |
