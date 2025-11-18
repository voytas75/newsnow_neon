"""Options panel builder for AINewsApp (appearance and behavior sections).

Updates: v0.52 - 2025-11-18 - Extracted settings UI into a view module.
"""
from __future__ import annotations

import tkinter as tk
from ...config import COLOR_PROFILES, CUSTOM_PROFILE_NAME, DEFAULT_COLOR_PROFILE_NAME


def _profile_name_options() -> list[str]:
    names = list(COLOR_PROFILES.keys())
    if CUSTOM_PROFILE_NAME not in COLOR_PROFILES:
        names.append(CUSTOM_PROFILE_NAME)
    else:
        names = [n for n in names if n != CUSTOM_PROFILE_NAME] + [CUSTOM_PROFILE_NAME]
    return names


def build_options_panel(app: tk.Tk) -> tk.Frame:
    """Create appearance and behavior settings sections."""
    settings_frame = tk.Frame(app.options_container, name="options", bg="black")
    settings_frame.pack(fill="x", pady=(0, 10))

    appearance_section = tk.Frame(settings_frame, bg="black")
    appearance_section.pack(side="left", fill="x", expand=True)

    behavior_section = tk.Frame(settings_frame, bg="black")
    behavior_section.pack(side="left", fill="x", expand=True, padx=(20, 0))

    appearance_header = tk.Label(
        appearance_section,
        text="Ticker Appearance",
        bg="black",
        fg="lightgray",
        font=("Segoe UI", 10, "bold"),
    )
    appearance_header.pack(anchor="w")

    profile_row = tk.Frame(appearance_section, bg="black")
    profile_row.pack(fill="x", pady=(6, 0))

    profile_names = _profile_name_options()
    app.color_profile_var = tk.StringVar(value=DEFAULT_COLOR_PROFILE_NAME)
    profile_label = tk.Label(profile_row, text="Profile:", bg="black", fg="lightgray")
    profile_label.pack(side="left")
    profile_menu = tk.OptionMenu(
        profile_row,
        app.color_profile_var,
        *profile_names,
        command=getattr(app, "_apply_color_profile"),
    )
    profile_menu.configure(bg="#2f2f2f", fg="white", highlightthickness=0)
    profile_menu["menu"].configure(bg="#2f2f2f", fg="white")
    profile_menu.pack(side="left", padx=(6, 0))
    app.profile_menu = profile_menu

    speed_row = tk.Frame(appearance_section, bg="black")
    speed_row.pack(fill="x", pady=(6, 0))
    speed_label = tk.Label(speed_row, text="Speed:", bg="black", fg="lightgray")
    speed_label.pack(side="left")
    app.ticker_speed_var = tk.IntVar(value=getattr(app, "ticker").speed)
    speed_spin = tk.Spinbox(
        speed_row,
        from_=1,
        to=20,
        increment=1,
        width=4,
        textvariable=app.ticker_speed_var,
        command=getattr(app, "_apply_speed"),
    )
    speed_spin.pack(side="left", padx=(6, 0))
    speed_spin.bind("<FocusOut>", getattr(app, "_apply_speed"))
    speed_spin.bind("<Return>", getattr(app, "_apply_speed"))

    color_row = tk.Frame(appearance_section, bg="black")
    color_row.pack(fill="x", pady=(6, 0))
    app.ticker_bg_var = tk.StringVar(value=str(getattr(app, "ticker")["bg"]))
    app.ticker_fg_var = tk.StringVar(
        value=getattr(app, "ticker").itemcget(getattr(app, "ticker").message_item, "fill")
    )
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

    reset_row = tk.Frame(appearance_section, bg="black")
    reset_row.pack(fill="x", pady=(8, 0))
    reset_button = tk.Button(reset_row, text="Reset Settings", command=getattr(app, "_reset_settings"))
    reset_button.pack(side="left")

    behavior_header = tk.Label(
        behavior_section,
        text="Behavior & Timing",
        bg="black",
        fg="lightgray",
        font=("Segoe UI", 10, "bold"),
    )
    behavior_header.pack(anchor="w")

    debug_row = tk.Frame(behavior_section, bg="black")
    debug_row.pack(fill="x", pady=(6, 0))
    app.debug_check = tk.Checkbutton(
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
    app.debug_check.pack(side="left")
    app.litellm_debug_check = tk.Checkbutton(
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
    app.litellm_debug_check.pack(side="left", padx=10)

    history_row = tk.Frame(behavior_section, bg="black")
    history_row.pack(fill="x", pady=(6, 0))
    app.historical_cache_check = tk.Checkbutton(
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
    app.historical_cache_check.pack(side="left")

    auto_row = tk.Frame(behavior_section, bg="black")
    auto_row.pack(fill="x", pady=(6, 0))
    app.auto_refresh_check = tk.Checkbutton(
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
    app.auto_refresh_check.pack(side="left")
    refresh_label = tk.Label(auto_row, text="Interval (min):", bg="black", fg="lightgray")
    refresh_label.pack(side="left", padx=(10, 2))
    app.auto_refresh_spin = tk.Spinbox(
        auto_row,
        from_=1,
        to=180,
        width=4,
        textvariable=getattr(app, "auto_refresh_minutes_var"),
        command=getattr(app, "_update_auto_refresh_minutes"),
    )
    app.auto_refresh_spin.pack(side="left")
    app.auto_refresh_spin.bind("<FocusOut>", getattr(app, "_update_auto_refresh_minutes"))
    app.auto_refresh_spin.bind("<Return>", getattr(app, "_update_auto_refresh_minutes"))

    refresh_status_row = tk.Frame(auto_row, bg="black")
    refresh_status_row.pack(side="left", padx=(16, 0))

    app.next_refresh_var = tk.StringVar(value="Next refresh: --:--")
    next_refresh_label = tk.Label(
        refresh_status_row,
        textvariable=app.next_refresh_var,
        bg="black",
        fg="#89CFF0",
        font=("Segoe UI", 10, "italic"),
    )
    next_refresh_label.pack(side="left")

    app.last_refresh_var = tk.StringVar(value="Last refresh: pending")
    last_refresh_label = tk.Label(
        refresh_status_row,
        textvariable=app.last_refresh_var,
        bg="black",
        fg="#89CFF0",
        font=("Segoe UI", 10, "italic"),
    )
    last_refresh_label.pack(side="left", padx=(12, 0))

    watch_row = tk.Frame(behavior_section, bg="black")
    watch_row.pack(fill="x", pady=(6, 0))
    app.background_watch_check = tk.Checkbutton(
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
    app.background_watch_check.pack(side="left")
    threshold_label = tk.Label(watch_row, text="Auto-refresh at:", bg="black", fg="lightgray")
    threshold_label.pack(side="left", padx=(10, 2))
    app.background_watch_threshold_spin = tk.Spinbox(
        watch_row,
        from_=1,
        to=999,
        width=4,
        textvariable=getattr(app, "background_watch_threshold_var"),
        command=getattr(app, "_apply_background_watch_threshold"),
    )
    app.background_watch_threshold_spin.pack(side="left")
    app.background_watch_threshold_spin.bind("<FocusOut>", getattr(app, "_apply_background_watch_threshold"))
    app.background_watch_threshold_spin.bind("<Return>", getattr(app, "_apply_background_watch_threshold"))
    threshold_suffix = tk.Label(watch_row, text="unseen headlines", bg="black", fg="lightgray")
    threshold_suffix.pack(side="left", padx=(4, 0))
    app.new_headlines_label = tk.Label(
        watch_row,
        textvariable=getattr(app, "new_headlines_var"),
        bg="black",
        fg="lightgray",
        font=("Segoe UI", 10, "italic"),
    )
    app.new_headlines_label.pack(side="left", padx=(12, 0))

    timezone_row = tk.Frame(behavior_section, bg="black")
    timezone_row.pack(fill="x", pady=(6, 0))
    timezone_label = tk.Label(timezone_row, text="Time Zone:", bg="black", fg="lightgray")
    timezone_label.pack(side="left")
    app.timezone_var = tk.StringVar(value=getattr(app, "_timezone_name"))
    app.timezone_menu = tk.OptionMenu(
        timezone_row,
        app.timezone_var,
        *getattr(app, "_timezone_options"),
    )
    app.timezone_menu.configure(bg="#2f2f2f", fg="white", highlightthickness=0)
    app.timezone_menu["menu"].configure(bg="#2f2f2f", fg="white")
    app.timezone_menu.pack(side="left", padx=(6, 0))
    # initial menu refresh is handled by application during settings load
    app.timezone_var.trace_add("write", getattr(app, "_on_timezone_change"))

    return settings_frame
