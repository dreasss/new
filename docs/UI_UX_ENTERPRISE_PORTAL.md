# Enterprise UI/UX Blueprint — Support Portal

## Design overview
Портал спроектирован как **единая рабочая среда поддержки** для трёх ролей: сотрудник (User), оператор (Support), администратор (Admin). Визуальный язык — спокойный enterprise-minimal: высокая читаемость, понятная иерархия, предсказуемые действия, быстрые сценарии без визуального шума.

Главный принцип: **всегда видно текущее состояние заявки и следующий шаг**. Интерфейс решает задачу «принять решение за 3–5 секунд»: что срочно, где риск SLA, что нужно сделать прямо сейчас.

## Принятые входные дефолты
- Бренд: **Northstar Industries IT Support**
- Логотип: **есть** (wordmark + compact icon)
- Фирменный цвет: `#2F6BFF`
- Доп. цвет: `#00A3A3`
- Язык по умолчанию: **RU** (EN как дополнительный)
- Аутентификация: **SSO (SAML/OIDC) + role-based access**
- Платформа: **desktop-first + адаптив для tablet/mobile**
- Доступность: **WCAG AA**, полная клавиатурная навигация

---

## Дизайн-токены

### Цвета
- **Brand / Primary**
  - `brand-600: #2F6BFF`
  - `brand-500: #4D81FF`
  - `brand-100: #E9F0FF`
- **Secondary / Accent**
  - `accent-600: #00A3A3`
  - `accent-100: #E6F7F7`
- **Neutrals**
  - `bg: #F7F9FC`
  - `surface: #FFFFFF`
  - `text-primary: #0F172A`
  - `text-secondary: #475569`
  - `text-muted: #64748B`
  - `border: #E2E8F0`
- **Status**
  - `success: #16A34A`
  - `warning: #D97706`
  - `error: #DC2626`
  - `info: #2563EB`
- **SLA urgency**
  - `sla-ok: #16A34A`
  - `sla-risk: #D97706`
  - `sla-breach: #DC2626`

### Типографика
- Font stack: `Inter, Segoe UI, Roboto, Arial, sans-serif`
- `H1`: 32/40, 700
- `H2`: 24/32, 700
- `H3`: 20/28, 600
- `Title`: 18/28, 600
- `Body`: 16/24, 400
- `Body-sm`: 14/20, 400
- `Caption`: 12/16, 500
- Кнопки: 14/20, 600

### Spacing и радиусы
- Шкала отступов: **4 / 8 / 12 / 16 / 24 / 32**
- Радиусы:
  - `sm: 10px`
  - `md: 16px`
  - `2xl: 24px`
- Тени:
  - `card-soft: 0 4px 20px rgba(15,23,42,0.06)`
  - `overlay: 0 12px 40px rgba(15,23,42,0.16)`

### Motion
- Hover/focus/expand: `150–200ms`, `ease-out`
- Без резких трансформаций и параллакса

---

## Информационная архитектура и экраны

## 1) SSO Login
**Layout**: центрированный auth-card + brand strip сверху.
- Заголовок: «Вход в портал техподдержки»
- Основная CTA: `Войти через корпоративный аккаунт`
- Secondary: `Переключить язык: RU / EN`
- Инфоблок: «Используется корпоративный SSO (SAML/OIDC)»

**Состояния**
- Loading: skeleton кнопки + текст «Проверяем параметры входа…»
- Error: «Сессия входа истекла. Повторите попытку.» + `Повторить`
- Access denied: «Недостаточно прав для портала» + код ошибки

## 2) User Dashboard
**Layout**: topbar + sidebar + main (2 колонки).
- Левая колонка: KPI-карточки (`Открытые`, `В работе`, `Ожидают вас`)
- Правая колонка: «Последние ответы поддержки»
- Быстрые действия: `Создать заявку`, `Открыть мои заявки`

**Состояния**
- Empty: «Заявок пока нет» + CTA `Создать первую заявку`
- Loading: skeleton KPI + список
- Error: «Не удалось загрузить данные дашборда» + `Повторить`
- Success feedback: toast «Заявка успешно создана»

## 3) Create Ticket
**Layout**: single-column form (ширина 760px), sticky action bar снизу.
- Поля:
  - Категория (select)
  - Тема (input)
  - Описание (textarea)
  - Вложения (drag&drop + кнопка)
  - Кабинет / Отдел
  - Предпочтительный канал: `Web` / `Телефон`
- Кнопки: `Создать заявку`, `Сохранить черновик`

**Валидации**
- Тема: 8–120 символов
- Описание: 20+ символов
- Вложения: допустимые форматы + размер
- Ошибки inline под полем

## 4) User Tickets List
**Layout**: toolbar (поиск + фильтры + сортировка) + таблица.
- Фильтры: статус, приоритет, категория
- Поиск: по номеру/теме
- Таблица: sticky header, пагинация

Колонки: `#`, `Тема`, `Статус`, `Приоритет`, `SLA`, `Обновлена`, `Канал`

**Состояния**
- Empty search: «По вашему запросу ничего не найдено» + `Сбросить фильтры`
- Loading: table skeleton rows
- Error: «Ошибка загрузки списка заявок» + retry

## 5) Ticket Details (User)
**Layout**: 3 зоны
- Header: номер, статус badge, priority pill, SLA индикатор
- Main: таймлайн + публичные комментарии
- Side panel: карточка заявки (категория, отдел, кабинет, исполнитель)

Действия:
- `Добавить комментарий`
- `Закрыть заявку` (если разрешено)
- `Оценить поддержку` (после CLOSED: 1–5 звёзд + короткий отзыв)

**Состояния**
- Empty comments: «Комментариев пока нет. Опишите обновление по проблеме.»
- Error attachment preview: код + `Скачать файл`

## 6) Support Queue (table + kanban toggle)
**Layout**: top toolbar + view switcher.
- Toggle: `Таблица | Канбан`
- Фильтры: статус, приоритет, исполнитель, канал, теги, отдел, кабинет
- SLA колоризация строк/карточек

Канбан-колонки:
- NEW
- IN_PROGRESS
- WAITING_USER
- RESOLVED

Card summary:
- #тикета, тема, пользователь, отдел/кабинет, SLA, приоритет, теги

## 7) Ticket Details (Support)
**Layout**: как user, плюс support actions rail.

Ключевые действия:
- `Взять в работу`
- `Делегировать`
- `Эскалировать`
- `Ответить пользователю`
- `Закрыть`

Блоки:
- Публичные комментарии
- Внутренние заметки (видны только support/admin)
- Шаблоны ответов
- История действий (audit trail)

## 8) Admin Wizard (stepper)
Шаги:
1. Брендинг
2. Фразы бота
3. Интеграции (SSO, SpeechKit)
4. Политики SLA
5. Роли и права
6. Подтверждение

Паттерн шага:
- слева контент шага
- справа sticky summary изменений
- кнопки: `Назад`, `Далее`, `Сохранить и применить`

## 9) Settings / Integrations / Health
**Layout**: табы `Интеграции | Безопасность | Health`
- Интеграции: статусы SSO/SpeechKit/Telephony
- Безопасность: токены/ограничения/сроки
- Health: `core-api`, `telephony-bot`, `web-portal`, `postgres`, `redis`

Health-карточка:
- статус
- last check
- latency
- CTA `Проверить снова`

---

## Компоненты design-system + состояния

### Навигация
- `Topbar` (поиск, язык, профиль, уведомления)
- `Sidebar` (сворачиваемый, группы разделов)
- `Breadcrumbs`

### Data entry / content
- `SearchInput`, `FilterChip`, `DateRange`
- `Table` (sticky header, плотность comfortable/compact)
- `Card` (метрики/сводка)
- `StatusBadge` (NEW/IN_PROGRESS/WAITING_USER/RESOLVED/CLOSED)
- `PriorityPill` (LOW/MED/HIGH/URGENT)
- `SLAIndicator` (цвет + таймер)
- `TicketTimeline`
- `CommentComposer` (markdown-light + attachments)
- `AttachmentList` (preview/download)
- `RatingWidget` (stars + short review)

### Feedback
- `Toast` (success/info/error)
- `InlineAlert`
- `ConfirmModal`
- `EmptyState` (иконка + объяснение + CTA)
- `ErrorState` (код/детали/Retry)
- `Skeleton` (table/card/form)

### Состояния компонентов
Для каждого ключевого компонента обязательны:
- loading
- empty (если применимо)
- error + retry
- disabled (нет прав/нет данных)
- focus-visible style (клавиатура)

---

## UX-правила и copy tone
- Единая терминология статусов без синонимов.
- CTA всегда глаголом действия: `Создать`, `Взять`, `Ответить`, `Закрыть`.
- Ошибки короткие и прикладные: «Файл превышает 20 МБ. Загрузите меньший файл.»
- Подсказки в формах только там, где повышают успех первого прохождения.

---

## Адаптив и responsive
- Breakpoints:
  - `>=1280`: desktop 3-column details
  - `1024–1279`: desktop compact
  - `768–1023`: tablet (sidebar overlay)
  - `<768`: mobile (bottom actions, приоритет карточек)
- Mobile-priority:
  - fixed bottom action bar для главных CTA
  - таблицы в карточки с ключевыми полями
  - sticky фильтры (горизонтальный скролл chip-ов)

---

## Accessibility checklist (WCAG AA)
- Контраст текста/фона не ниже AA.
- Полная навигация с клавиатуры (Tab/Shift+Tab/Enter/Esc).
- Видимый `focus ring` для интерактивных элементов.
- `aria-label` для иконок без текста.
- Ошибки форм озвучиваемы скринридером (`aria-live="polite"`).
- Диалоги имеют trap focus и закрытие по Esc.
- Не полагаться только на цвет для статусов (добавлять текст/иконку).
