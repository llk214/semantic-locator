"""
Internationalization (i18n) module for Locus PDF Search.
Supports Chinese (Simplified) and English with runtime switching.
"""

# Default language
_current_lang = "zh"

# Translation dictionary: key -> {lang_code: text}
_STRINGS = {
    # ===== Splash Screen =====
    "splash.tagline": {
        "en": "Smart PDF Search for Students & Researchers",
        "zh": "面向学生和研究者的智能PDF搜索工具",
    },
    "splash.initializing": {
        "en": "Initializing...",
        "zh": "正在初始化...",
    },
    "splash.loading_libs": {
        "en": "Loading libraries...",
        "zh": "正在加载库文件...",
    },
    "splash.loading_ui": {
        "en": "Loading UI components...",
        "zh": "正在加载界面组件...",
    },
    "splash.loading_engine": {
        "en": "Loading search engine...",
        "zh": "正在加载搜索引擎...",
    },
    "splash.starting": {
        "en": "Starting application...",
        "zh": "正在启动应用...",
    },
    "splash.ready": {
        "en": "Ready!",
        "zh": "就绪！",
    },

    # ===== Window Title =====
    "app.title": {
        "en": "📚 Locus - PDF Search",
        "zh": "📚 Locus - PDF智能搜索",
    },

    # ===== Top Frame - Directory =====
    "dir.label": {
        "en": "PDF Directory:",
        "zh": "PDF文件夹：",
    },
    "dir.placeholder": {
        "en": "Select a folder with PDFs...",
        "zh": "请选择包含PDF的文件夹...",
    },
    "dir.browse": {
        "en": "Browse",
        "zh": "浏览",
    },
    "dir.load_index": {
        "en": "Load Index",
        "zh": "加载索引",
    },

    # ===== Status =====
    "status.select_dir": {
        "en": "Select a directory with PDFs",
        "zh": "请选择包含PDF的文件夹",
    },
    "status.loading": {
        "en": "Loading...",
        "zh": "加载中...",
    },
    "status.step1_model": {
        "en": "Step 1/2: Loading model...",
        "zh": "步骤 1/2：正在加载模型...",
    },
    "status.step2_indexing": {
        "en": "Step 2/2: Indexing PDF files...",
        "zh": "步骤 2/2：正在索引PDF文件...",
    },
    "status.step1_deep": {
        "en": "Step 1/2: Loading model...",
        "zh": "步骤 1/2：正在加载模型...",
    },
    "status.step2_deep": {
        "en": "Step 2/3: Indexing PDF files...",
        "zh": "步骤 2/3：正在索引PDF文件...",
    },
    "status.step3_deep": {
        "en": "Step 3/3: Computing embeddings ({current}/{total})...",
        "zh": "步骤 3/3：正在计算向量 ({current}/{total})...",
    },
    "status.deep_indexing": {
        "en": "🔬 Deep indexing: {current}/{total} pages ({percent}%)",
        "zh": "🔬 深度索引中：{current}/{total} 页 ({percent}%)",
    },
    "status.ready_indexed": {
        "en": "✅ Ready! Indexed {count} pages ({mode} mode)",
        "zh": "✅ 就绪！已索引 {count} 页（{mode}模式）",
    },
    "status.mode_fast": {
        "en": "Fast",
        "zh": "快速",
    },
    "status.mode_deep": {
        "en": "Deep",
        "zh": "深度",
    },
    "status.error": {
        "en": "❌ Error: {msg}",
        "zh": "❌ 出错：{msg}",
    },
    "status.quality_changed": {
        "en": "Quality changed - click 'Load Index' to apply",
        "zh": "质量已更改 - 点击「加载索引」以应用",
    },
    "status.search_error": {
        "en": "❌ Search error: {msg}",
        "zh": "❌ 搜索出错：{msg}",
    },
    "status.cross_lingual": {
        "en": "🌍 Cross-lingual: {count} results (semantic only)",
        "zh": "🌍 跨语言搜索：{count} 条结果（仅语义）",
    },
    "status.found_results": {
        "en": "✅ Found {count} results",
        "zh": "✅ 找到 {count} 条结果",
    },
    "status.opening": {
        "en": "Opening {name} at page {page}...",
        "zh": "正在打开 {name} 第 {page} 页...",
    },
    "status.opened": {
        "en": "✅ Opened {name} at page {page}",
        "zh": "✅ 已打开 {name} 第 {page} 页",
    },
    "status.opened_no_nav": {
        "en": "⚠️ Opened {name} (page navigation may not be supported)",
        "zh": "⚠️ 已打开 {name}（可能不支持页面跳转）",
    },
    "status.model_downloaded": {
        "en": "✅ {quality} model already downloaded",
        "zh": "✅ {quality} 模型已下载",
    },
    "status.downloading": {
        "en": "⬇️ Downloading {quality} ({size})...",
        "zh": "⬇️ 正在下载 {quality}（{size}）...",
    },
    "status.downloading_init": {
        "en": "⬇️ Initializing download for {quality}...",
        "zh": "⬇️ 正在初始化 {quality} 下载...",
    },
    "status.verifying": {
        "en": "⬇️ Verifying {quality} model...",
        "zh": "⬇️ 正在验证 {quality} 模型...",
    },
    "status.download_ok": {
        "en": "✅ Downloaded {quality} model successfully!",
        "zh": "✅ {quality} 模型下载成功！",
    },
    "status.download_fail": {
        "en": "❌ Download failed: {msg}",
        "zh": "❌ 下载失败：{msg}",
    },
    "status.deleted_model": {
        "en": "Deleted {quality} model",
        "zh": "已删除 {quality} 模型",
    },

    # ===== Search Frame =====
    "search.label": {
        "en": "Search:",
        "zh": "搜索：",
    },
    "search.placeholder": {
        "en": "Describe what you want to find…",
        "zh": "描述你想查找的内容…",
    },
    "search.button": {
        "en": "🔍 Search",
        "zh": "🔍 搜索",
    },
    "search.searching": {
        "en": "🔍 Searching",
        "zh": "🔍 搜索中",
    },

    # ===== Options Frame =====
    "options.semantic": {
        "en": "🧠 Semantic",
        "zh": "🧠 语义",
    },
    "options.literal": {
        "en": "🔤 Literal",
        "zh": "🔤 关键词",
    },
    "options.results": {
        "en": "Results:",
        "zh": "结果数：",
    },
    "options.quality": {
        "en": "Quality:",
        "zh": "质量：",
    },

    # ===== Quality Options =====
    "quality.balanced": {
        "en": "⚖️ Balanced",
        "zh": "⚖️ 均衡",
    },
    "quality.high": {
        "en": "🎯 High Accuracy",
        "zh": "🎯 高精度",
    },
    "quality.best": {
        "en": "🚀 Best",
        "zh": "🚀 最佳",
    },
    "quality.multilingual": {
        "en": "🌍 Multilingual",
        "zh": "🌍 多语言",
    },

    # ===== Model Management Dialog =====
    "models.section_en": {
        "en": "English Models",
        "zh": "英文模型",
    },
    "models.section_zh": {
        "en": "Chinese Models",
        "zh": "中文模型",
    },
    "models.section_multi": {
        "en": "Multilingual Models",
        "zh": "多语言模型",
    },

    # ===== Results =====
    "results.placeholder": {
        "en": "Search results will appear here...",
        "zh": "搜索结果将在此处显示...",
    },
    "results.no_results": {
        "en": "No results found. Try different keywords.",
        "zh": "未找到结果，请尝试其他关键词。",
    },
    "results.page": {
        "en": "Page {num}",
        "zh": "第 {num} 页",
    },

    # ===== Bottom Frame =====
    "bottom.open_pdf": {
        "en": "📄 Open PDF at Page",
        "zh": "📄 打开PDF对应页",
    },
    "bottom.double_click_hint": {
        "en": "(or double-click a result)",
        "zh": "（或双击搜索结果）",
    },
    "bottom.snippet": {
        "en": "Full Snippet:",
        "zh": "完整片段：",
    },

    # ===== Dialogs =====
    "dialog.warning": {
        "en": "Warning",
        "zh": "警告",
    },
    "dialog.error": {
        "en": "Error",
        "zh": "错误",
    },
    "dialog.info": {
        "en": "Info",
        "zh": "提示",
    },
    "dialog.load_index_first": {
        "en": "Please load an index first",
        "zh": "请先加载索引",
    },
    "dialog.select_result": {
        "en": "Please select a result first",
        "zh": "请先选择一个结果",
    },
    "dialog.pdf_not_found": {
        "en": "PDF not found: {path}",
        "zh": "未找到PDF文件：{path}",
    },
    "dialog.invalid_dir": {
        "en": "Please select a valid directory",
        "zh": "请选择一个有效的文件夹",
    },
    "dialog.model_required": {
        "en": "Model Required",
        "zh": "需要模型",
    },
    "dialog.download_model_first": {
        "en": "Please download the {quality} model first.\nClick the ⬇️ button next to the quality selector.",
        "zh": "请先下载 {quality} 模型。\n点击质量选择器旁的 ⬇️ 按钮。",
    },

    # ===== Index Mode Dialog =====
    "index_dialog.title": {
        "en": "Choose Index Mode",
        "zh": "选择索引模式",
    },
    "index_dialog.question": {
        "en": "How would you like to index?",
        "zh": "请选择索引方式",
    },
    "index_dialog.fast": {
        "en": "⚡ Fast Index",
        "zh": "⚡ 快速索引",
    },
    "index_dialog.fast_desc": {
        "en": "Quick startup, good for small collections\nMay miss semantically related pages",
        "zh": "启动快速，适合小型文档集\n可能遗漏语义相关的页面",
    },
    "index_dialog.deep": {
        "en": "🔬 Deep Index",
        "zh": "🔬 深度索引",
    },
    "index_dialog.deep_desc": {
        "en": "Slower startup, best for large collections\nFinds all related content",
        "zh": "启动较慢，适合大型文档集\n能找到所有相关内容",
    },
    "index_dialog.cancel": {
        "en": "Cancel",
        "zh": "取消",
    },

    # ===== Model Management =====
    "models.title": {
        "en": "Manage Models",
        "zh": "管理模型",
    },
    "models.header": {
        "en": "Downloaded Models",
        "zh": "已下载的模型",
    },
    "models.builtin": {
        "en": "Built-in",
        "zh": "内置",
    },
    "models.none": {
        "en": "No models downloaded yet",
        "zh": "尚未下载任何模型",
    },
    "models.downloaded_size": {
        "en": "Downloaded: {size} MB",
        "zh": "已下载：{size} MB",
    },
    "models.close": {
        "en": "Close",
        "zh": "关闭",
    },
    "models.delete": {
        "en": "Delete",
        "zh": "删除",
    },
    "models.delete_confirm_title": {
        "en": "Delete Model",
        "zh": "删除模型",
    },
    "models.delete_confirm": {
        "en": "Delete {quality} model?\nYou'll need to re-download it to use this quality level.",
        "zh": "确定删除 {quality} 模型吗？\n重新使用该质量级别时需要重新下载。",
    },
    "models.download_error_title": {
        "en": "Download Error",
        "zh": "下载错误",
    },
    "models.download_error": {
        "en": "Failed to download {quality} model.\n\nError: {error}\n\nPlease check your internet connection and try again.",
        "zh": "下载 {quality} 模型失败。\n\n错误：{error}\n\n请检查网络连接后重试。",
    },

    # ===== Download Animation =====
    "download.downloading": {
        "en": "⬇️ Downloading",
        "zh": "⬇️ 下载中",
    },

    # ===== Language Toggle =====
    "lang.switch": {
        "en": "中文",
        "zh": "English",
    },
}


def get_lang() -> str:
    """Get current language code."""
    return _current_lang


def set_lang(lang: str):
    """Set current language ('en' or 'zh')."""
    global _current_lang
    if lang in ("en", "zh"):
        _current_lang = lang


def t(key: str, **kwargs) -> str:
    """
    Translate a key to the current language.
    Supports format placeholders via kwargs: t("status.ready", count=5)
    """
    entry = _STRINGS.get(key)
    if entry is None:
        return key  # Fallback: return key itself

    text = entry.get(_current_lang, entry.get("en", key))

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass  # If formatting fails, return unformatted text

    return text