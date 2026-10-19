# GitHub publication information

**Repository name:** `rfq-workbench`

**Display name:** RFQ Workbench

**Description:** Unfinished local-first procurement beta: extract enquiry documents with Ollama, review product lines and prepare RFQ Excel templates. Gmail, pricing and full quotation workflow are planned.

**Suggested topics:** `python`, `ollama`, `procurement`, `rfq`, `document-processing`, `ocr`, `portfolio`, `work-in-progress`, `sqlite`

**Project status:** Unfinished portfolio beta / work in progress. Do not describe it as a completed client delivery, an end-to-end procurement platform or production-ready software.

**Portfolio text:** I built a local procurement prototype that extracts product lines from documents using a local model, supports source-based human review, and prepares category-specific RFQ text and Excel reply templates. It includes persistent records, OCR previews and automated tests. Gmail/Sheets integration, supplier reply processing, pricing and the remaining quotation workflow are unfinished. If the repository receives enough stars and community interest, I will publish updates and complete the remaining features myself.

## Публикация вручную

1. Открой `https://github.com/new` и выбери имя `rfq-workbench`.
2. В Description вставь описание выше. Выбери Public. README уже входит в проект: не создавай второй при создании репозитория.
3. Для загрузки через браузер открой созданный репозиторий → uploading an existing file / Add file → Upload files. Перетащи содержимое этой экспортной папки, сохранив вложенные каталоги. Не загружай внешнюю папку как дополнительный уровень.
4. Убедись, что в загрузке нет `data`, `.env`, ключей, паролей, рабочих документов, `node_modules`, `.venv` и `__pycache__`. Они исключены из подготовленного экспорта.
5. Нажми Commit changes. Проверь, что на главной странице видны README, предупреждение о незавершённой бете и ссылка на ROADMAP.
6. В About добавь описание и topics. Website можно оставить пустым: публичный сервер у этой беты не развёрнут.

Запуск описан в `README.md` и `docs/LOCAL-SETUP-RU.md`. Получателю потребуется Python и локальная Ollama с совместимой моделью; Python-зависимости устанавливаются из requirements. Экспорт не содержит установленную модель или личную рабочую базу. Выбор открытой лицензии остаётся за владельцем: публикация исходников сама по себе не задаёт лицензию.
