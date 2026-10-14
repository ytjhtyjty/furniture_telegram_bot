start_kb = [
    ("🛏 Спальная мебель", "sleep_furniture"),
    ("🍳 Кухонная мебель", "kitchen_furniture"),
    ("🛋 Мягкая мебель", "soft_furniture"),
    ("📚 Столы и стулья", "tables_chairs"),
    ("📺 Тумбы и комоды", "cabinets_commodes"),
    ("🛏 Кровати", "bed_furniture"),
    ("🛏 Матрасы", "mattresses"),
    ("🚪 Шкафы", "wardrobes"),
    ("ℹ️ О компании / Контакты", "about_company"),
    ("🤝 Сотрудничество", "cooperation_company"),
]

furniture_types_kb = [
    (text, cb) for text, cb in start_kb
    if cb not in ("about_company", "cooperation_company")
]

admin_kb = [
    ("➕ Добавить категорию", "new_category_furniture"),
    ("🪑 Добавить мебель", "new_furniture"),
    ("🗑 Удалить мебель", "remove_furniture"),
    ("🗂 Удалить категорию", "remove_category"),
    ("📋 Список категорий", "list_categories_furniture"),
    ("🤝 Заявки", "cooperation_requests"),
    ("⬅️ Назад", "back_to_main"),
]

build_cancel_kb = [("❌ Отменить", "cancel_category")]
furniture_cancel_kb = [("❌ Отменить", "cancel_furniture")]

skip_description_kb = [("⏭ Пропустить", "skip_category_description")]

finish_furniture_kb = [("✅ Завершить добавление", "finish_furniture_creation")]

country_of_origin_kb = [
    ("🇷🇺 Россия", "russian_origin"),
    ("🇹🇷 Турция", "turkey_origin"),
    ("⬅️ Назад", "back_to_main"),
]

kitchen_subcategory_inline_kb = [
    ("📏 Прямая кухня", "straight_kitchen"),
    ("📐 Угловая кухня", "corner_kitchen"),
    ("⬅️ Назад", "back_to_main"),
]
