"""
Options panel view builder for NewsNow Neon.
Builds the appearance and behavior sections inside the options container.
"""

import tkinter as tk
from typing import Optional


def build_options_panel(app: tk.Tk) -> tk.Frame:
    """
    Build the options/settings panel for the application.

    This view is intentionally logic-free; it wires widget commands to methods
    already implemented on the orchestrator (AINewsApp) controllers.

    Returns the settings frame container.
    """
    # Parent container
    parent: Optional[tk.Frame] = getattr(app, "options_container", None)
    if parent is None or not isinstance(parent, tk.Frame):
        parent = tk.Frame(app, name="options_container", bg="black")
        parent.pack(fill="x", padx=10, pady=(0, 10))
        setattr(app, "options_container", parent)

    settings_frame = tk.Frame(parent, name="options", bg="black")
    settings_frame.pack(fill="x", pady=(0, 10))

    # Left: appearance section
    appearance_section = tk.Frame(settings_frame, bg="black")
    appearance_section.pack(side="left", fill="x", expand=True)

    # Right: behavior section
    behavior_section = tk.Frame(settings_frame, bg="black")
    behavior_section.pack(side="left", fill="x", expand=True, padx=(20, 0))

    # Appearance header
    appearance_header = tk.Label(
        appearance_section,
        text="Ticker Appearance",
        bg="black",
        fg="lightgray",
        font=("Segoe UI", 10, "bold"),
    )
    appearance_header.pack(anchor="w")

    # Profile row
    profile_row = tk.Frame(appearance_section, bg="black")
    profile_row.pack(fill="x", pady=(6, 0))

    profile_label = tk.Label(profile_row, text="Profile:", bg="black", fg="lightgray")
    profile_label.pack(side="left")

    # Create with a minimal option; app._refresh_profile_menu will populate
    current_profile = getattr(app, "color_profile_var").get()
    profile_menu = tk.OptionMenu(
        profile_row,
        getattr(app, "color_profile_var"),
        current_profile,
        command=getattr(app, "_apply_color_profile"),
    )
    profile_menu.configure(bg="#2f2f2f", fg="white", highlightthickness=0)
    profile_menu["menu"].configure(bg="#2f2f2f", fg="white")
    profile_menu.pack(side="left", padx=(6, 0))
    setattr(app, "profile_menu", profile_menu)
    # Ensure menu options are populated by the app helper
    try:
        getattr(app, "_refresh_profile_menu")()
    except Exception:
        pass

    # Speed row
    speed_row = tk.Frame(appearance_section, bg="black")
    speed_row.pack(fill="x", pady=(6, 0))

    speed_label = tk.Label(speed_row, text="Speed:", bg="black", fg="lightgray")
    speed_label.pack(side="left")

    speed_spin = tk.Spinbox(
        speed_row,
        from_=1,
        to=20,
        increment=1,
        width=4,
        textvariable=getattr(app, "ticker_speed_var"),
        command=getattr(app, "_apply_speed"),
    )
    speed_spin.pack(side="left", padx=(6, 0))
    speed_spin.bind("<FocusOut>", getattr(app, "_apply_speed"))
    speed_spin.bind("<Return>", getattr(app, "_apply_speed"))

    # Color row
    color_row = tk.Frame(appearance_section, bg="black")
    color_row.pack(fill="x", pady=(6, 0))

    bg_button = tk.Button(
        color_row,
        text="Background Color…",
        command=lambda: getattr(app, "_choose_color")("background"),
    )
    bg_button.pack(side="left")

    fg_button = tk.Button(
        color_row,
        text="Text Color…",
        command=lambda: getattr(app, "_choose_color")("text"),
    )
    fg_button.pack(side="left", padx=6)

    # Reset row
    reset_row = tk.Frame(appearance_section, bg="black")
    reset_row.pack(fill="x", pady=(8, 0))

    reset_button = tk.Button(
        reset_row, text="Reset Settings", command=getattr(app, "_reset_settings")
    )
    reset_button.pack(side="left")

    # Behavior header
    behavior_header = tk.Label(
        behavior_section,
        text="Behavior & Timing",
        bg="black",
        fg="lightgray",
        font=("Segoe UI", 10, "bold"),
    )
    behavior_header.pack(anchor="w")

    # Debug/LiteLLM row
    debug_row = tk.Frame(behavior_section, bg="black")
    debug_row.pack(fill="x", pady=(6, 0))

    debug_check = tk.Checkbutton(
        debug_row,
        text="Debug Logs",
        variable=getattr(app, "debug_var"),
        command=getattr(app, "_toggle_debug_mode"),
        bg="black",
        fg="lightgray",
        selectcolor="#202020",
        activebackground="black",
        activeforeground="white",
        highlightthickness=0,
    )
    debug_check.pack(side="left")

    litellm_debug_check = tk.Checkbutton(
        debug_row,
        text="LiteLLM Debug",
        variable=getattr(app, "litellm_debug_var"),
        command=getattr(app, "_toggle_litellm_debug"),
        bg="black",
        fg="lightgray",
        selectcolor="#202020",
        activebackground="black",
        activeforeground="white",
        highlightthickness=0,
    )
    litellm_debug_check.pack(side="left", padx=10)

    # History row
    history_row = tk.Frame(behavior_section, bg="black")
    history_row.pack(fill="x", pady=(6, 0))

    historical_cache_check = tk.Checkbutton(
        history_row,
        text="Keep 24h History",
        variable=getattr(app, "historical_cache_var"),
        command=getattr(app, "_toggle_historical_cache"),
        bg="black",
        fg="lightgray",
        selectcolor="#202020",
        activebackground="black",
        activeforeground="white",
        highlightthickness=0,
    )
    historical_cache_check.pack(side="left")

    # Auto refresh row
    auto_row = tk.Frame(behavior_section, bg="black")
    auto_row.pack(fill="x", pady=(6, 0))

    auto_refresh_check = tk.Checkbutton(
        auto_row,
        text="Auto Refresh",
        variable=getattr(app, "auto_refresh_var"),
        command=getattr(app, "_toggle_auto_refresh"),
        bg="black",
        fg="lightgray",
        selectcolor="#202020",
        activebackground="black",
        activeforeground="white",
        highlightthickness=0,
    )
    auto_refresh_check.pack(side="left")

    refresh_label = tk.Label(
        auto_row, text="Interval (min):", bg="black", fg="lightgray"
    )
    refresh_label.pack(side="left", padx=(10, 2))

    auto_refresh_spin = tk.Spinbox(
        auto_row,
        from_=1,
        to=180,
        width=4,
        textvariable=getattr(app, "auto_refresh_minutes_var"),
        command=getattr(app, "_update_auto_refresh_minutes"),
    )
    auto_refresh_spin.pack(side="left")
    auto_refresh_spin.bind("<FocusOut>", getattr(app, "_update_auto_refresh_minutes"))
    auto_refresh_spin.bind("<Return>", getattr(app, "_update_auto_refresh_minutes"))

    # Refresh status row
    refresh_status_row = tk.Frame(auto_row, bg="black")
    refresh_status_row.pack(side="left", padx=(16, 0))

    next_refresh_label = tk.Label(
        refresh_status_row,
        textvariable=getattr(app, "next_refresh_var"),
        bg="black",
        fg="#89CFF0",
        font=("Segoe UI", 10, "italic"),
    )
    next_refresh_label.pack(side="left")

    last_refresh_label = tk.Label(
        refresh_status_row,
        textvariable=getattr(app, "last_refresh_var"),
        bg="black",
        fg="#89CFF0",
        font=("Segoe UI", 10, "italic"),
    )
    last_refresh_label.pack(side="left", padx=(12, 0))

    # Background watch row
    watch_row = tk.Frame(behavior_section, bg="black")
    watch_row.pack(fill="x", pady=(6, 0))

    background_watch_check = tk.Checkbutton(
        watch_row,
        text="Background Watch",
        variable=getattr(app, "background_watch_var"),
        command=getattr(app, "_toggle_background_watch"),
        bg="black",
        fg="lightgray",
        selectcolor="#202020",
        activebackground="black",
        activeforeground="white",
        highlightthickness=0,
    )
    background_watch_check.pack(side="left")

    threshold_label = tk.Label(
        watch_row, text="Auto-refresh at:", bg="black", fg="lightgray"
    )
    threshold_label.pack(side="left", padx=(10, 2))

    background_watch_threshold_spin = tk.Spinbox(
        watch_row,
        from_=1,
        to=999,
        width=4,
        textvariable=getattr(app, "background_watch_threshold_var"),
        command=getattr(app, "_apply_background_watch_threshold"),
    )
    background_watch_threshold_spin.pack(side="left")
    background_watch_threshold_spin.bind(
        "<FocusOut>", getattr(app, "_apply_background_watch_threshold")
    )
    background_watch_threshold_spin.bind(
        "<Return>", getattr(app, "_apply_background_watch_threshold")
    )

    threshold_suffix = tk.Label(
        watch_row, text="unseen headlines", bg="black", fg="lightgray"
    )
    threshold_suffix.pack(side="left", padx=(4, 0))

    new_headlines_label = tk.Label(
        watch_row,
        textvariable=getattr(app, "new_headlines_var"),
        bg="black",
        fg="lightgray",
        font=("Segoe UI", 10, "italic"),
    )
    new_headlines_label.pack(side="left", padx=(12, 0))
    setattr(app, "new_headlines_label", new_headlines_label)

    # Timezone row
    timezone_row = tk.Frame(behavior_section, bg="black")
    timezone_row.pack(fill="x", pady=(6, 0))

    timezone_label = tk.Label(
        timezone_row, text="Time Zone:", bg="black", fg="lightgray"
    )
    timezone_label.pack(side="left")

    timezone_menu = tk.OptionMenu(
        timezone_row,
        getattr(app, "timezone_var"),
        *getattr(app, "_timezone_options"),
    )
    timezone_menu.configure(bg="#2f2f2f", fg="white", highlightthickness=0)
    timezone_menu["menu"].configure(bg="#2f2f2f", fg="white")
    timezone_menu.pack(side="left", padx=(6, 0))
    setattr(app, "timezone_menu", timezone_menu)

    try:
        getattr(app, "_refresh_timezone_menu")()
    except Exception:
        pass

    return settings_frame