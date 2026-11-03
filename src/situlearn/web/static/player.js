(() => {
  "use strict";

  const audio = new Audio();
  audio.preload = "metadata";

  const slug = document.body.dataset.reportSlug || "";
  const progressKey = `situlearn:progress:${slug}`;
  const state = {
    playlist: [],
    index: 0,
    label: "",
    sectionId: null,
    kind: "chapter",
  };

  let player;
  let toggleButton;
  let previousButton;
  let nextButton;
  let seekInput;
  let labelElement;
  let timeElement;
  let resumePrompt;
  let lastSavedAt = 0;

  function formatTime(value) {
    if (!Number.isFinite(value) || value < 0) return "00:00";
    const total = Math.floor(value);
    return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(
      total % 60
    ).padStart(2, "0")}`;
  }

  function parsePlaylist(raw) {
    try {
      const values = JSON.parse(raw);
      return Array.isArray(values) ? values.filter(Boolean) : [];
    } catch (_error) {
      return [];
    }
  }

  function controlButton(className, label, text) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.setAttribute("aria-label", label);
    button.textContent = text;
    return button;
  }

  function buildPlayer() {
    player = document.createElement("div");
    player.className = "player";
    player.id = "player";
    player.hidden = true;

    const inner = document.createElement("div");
    inner.className = "player-inner";

    previousButton = controlButton(
      "player-prev",
      document.body.dataset.prevLabel || "上一章",
      "⏮"
    );
    toggleButton = controlButton("player-toggle", "播放或暂停", "▶");
    nextButton = controlButton(
      "player-next",
      document.body.dataset.nextLabel || "下一章",
      "⏭"
    );

    const main = document.createElement("div");
    main.className = "player-main";
    labelElement = document.createElement("div");
    labelElement.className = "player-label";
    labelElement.textContent = "未播放";
    seekInput = document.createElement("input");
    seekInput.className = "player-seek";
    seekInput.type = "range";
    seekInput.min = "0";
    seekInput.max = "100";
    seekInput.step = "0.1";
    seekInput.value = "0";
    seekInput.setAttribute("aria-label", "播放进度");
    main.append(labelElement, seekInput);

    timeElement = document.createElement("div");
    timeElement.className = "player-time";
    timeElement.textContent = "00:00 / 00:00";

    inner.append(previousButton, toggleButton, main, timeElement, nextButton);
    player.append(inner);
    document.body.append(player);

    player.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;
      if (target.closest(".player-toggle")) {
        togglePlayback();
      } else if (target.closest(".player-prev")) {
        playPrevious();
      } else if (target.closest(".player-next")) {
        playNext();
      }
    });

    seekInput.addEventListener("input", () => {
      if (Number.isFinite(audio.duration) && audio.duration > 0) {
        audio.currentTime = (Number(seekInput.value) / 100) * audio.duration;
      }
    });
  }

  function updateLabel() {
    if (!labelElement) return;
    if (!state.playlist.length) {
      labelElement.textContent = "未播放";
      return;
    }
    const position =
      state.playlist.length > 1
        ? ` · ${state.index + 1}/${state.playlist.length}`
        : "";
    const remaining =
      Number.isFinite(audio.duration) && audio.duration > 0
        ? ` · 剩余 ${formatTime(audio.duration - audio.currentTime)}`
        : "";
    labelElement.textContent = `${state.label}${position}${remaining}`;
  }

  function updateControls() {
    if (!toggleButton) return;
    toggleButton.textContent = audio.paused ? "▶" : "⏸";
    toggleButton.setAttribute("aria-label", audio.paused ? "播放" : "暂停");
    previousButton.disabled = state.index <= 0;
    nextButton.disabled = state.index + 1 >= state.playlist.length;
  }

  function updateSeek() {
    if (!seekInput) return;
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
    const current = Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
    seekInput.value = duration ? String((current / duration) * 100) : "0";
    timeElement.textContent = `${formatTime(current)} / ${formatTime(duration)}`;
    updateLabel();
    updateMediaPosition();
  }

  function updateMediaSession() {
    if (!("mediaSession" in navigator)) return;
    if (state.label) {
      try {
        navigator.mediaSession.metadata = new MediaMetadata({
          title: state.label,
          artist: document.title,
          album: "情景学习",
        });
      } catch (_error) {
        // MediaMetadata may be unavailable in older embedded webviews.
      }
    }
    navigator.mediaSession.playbackState = audio.paused ? "paused" : "playing";
  }

  function updateMediaPosition() {
    if (!("mediaSession" in navigator) || typeof navigator.mediaSession.setPositionState !== "function") {
      return;
    }
    if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;
    try {
      navigator.mediaSession.setPositionState({
        duration: audio.duration,
        playbackRate: audio.playbackRate || 1,
        position: Math.min(audio.currentTime || 0, audio.duration),
      });
    } catch (_error) {
      // Some browsers reject position state while the media is not active.
    }
  }

  function updateHighlight() {
    document.querySelectorAll("[data-section-id]").forEach((element) => {
      const matches =
        state.kind === "chapter" && element.dataset.sectionId === state.sectionId;
      element.classList.toggle("is-playing", matches);
    });
  }

  function saveProgress(force = false) {
    if (state.kind !== "chapter" || !state.sectionId || !state.playlist.length) {
      return;
    }
    const now = Date.now();
    if (!force && now - lastSavedAt < 5_000) return;
    lastSavedAt = now;
    const payload = {
      version: 1,
      section_id: state.sectionId,
      asset_index: state.index,
      current_time_s: Number((audio.currentTime || 0).toFixed(1)),
      updated_at: new Date().toISOString(),
    };
    try {
      localStorage.setItem(progressKey, JSON.stringify(payload));
    } catch (_error) {
      // Storage can be disabled or full; playback must keep working.
    }
  }

  function loadIndex(index, { autoplay = true, startTime = 0 } = {}) {
    if (index < 0 || index >= state.playlist.length) return;
    state.index = index;
    audio.src = state.playlist[index];
    audio.load();
    if (startTime > 0) {
      audio.addEventListener(
        "loadedmetadata",
        () => {
          const duration = Number.isFinite(audio.duration)
            ? audio.duration
            : startTime;
          audio.currentTime = Math.min(startTime, duration);
        },
        { once: true }
      );
    }
    if (autoplay) {
      audio.play().catch(() => {
        updateControls();
      });
    }
    updateControls();
    updateHighlight();
    updateMediaSession();
    updateLabel();
  }

  function setPlaylist(items, options = {}) {
    if (!items.length || !player) return;
    state.playlist = items;
    state.label = options.label || "正在播放";
    state.sectionId = options.sectionId || null;
    state.kind = options.kind || "chapter";
    player.hidden = false;
    document.body.classList.add("has-player");
    hideResumePrompt();
    loadIndex(options.startIndex || 0, {
      autoplay: options.autoplay !== false,
      startTime: options.startTime || 0,
    });
  }

  function togglePlayback() {
    if (!state.playlist.length) return;
    if (audio.paused) {
      audio.play().catch(() => {});
    } else {
      audio.pause();
    }
  }

  function playPrevious() {
    if (state.index > 0) {
      loadIndex(state.index - 1);
    } else if (state.playlist.length) {
      audio.currentTime = 0;
    }
  }

  function playNext() {
    if (state.index + 1 < state.playlist.length) {
      loadIndex(state.index + 1);
    }
  }

  function hideResumePrompt() {
    if (resumePrompt) {
      resumePrompt.remove();
      resumePrompt = null;
    }
  }

  function showResumePrompt(saved, button) {
    hideResumePrompt();
    resumePrompt = document.createElement("div");
    resumePrompt.className = "resume-prompt";
    resumePrompt.setAttribute("role", "status");

    const text = document.createElement("span");
    text.textContent = `上次听到「${button.dataset.label || document.body.dataset.thisSection || "本节"}」`;
    const resume = controlButton("resume-continue", "继续上次播放", "继续");
    const dismiss = controlButton("resume-dismiss", "关闭提示", "忽略");
    resume.addEventListener("click", () => {
      setPlaylist(parsePlaylist(button.dataset.srcs), {
        label: button.dataset.label,
        sectionId: saved.section_id,
        kind: "chapter",
        startIndex: Number(saved.asset_index) || 0,
        startTime: Number(saved.current_time_s) || 0,
      });
    });
    dismiss.addEventListener("click", hideResumePrompt);
    resumePrompt.append(text, resume, dismiss);
    document.body.append(resumePrompt);
  }

  function restoreProgress() {
    if (!slug) return;
    let saved;
    try {
      saved = JSON.parse(localStorage.getItem(progressKey) || "null");
    } catch (_error) {
      return;
    }
    if (!saved || saved.version !== 1 || !saved.section_id) return;
    const buttons = Array.from(document.querySelectorAll(".play[data-section-id]"));
    const button = buttons.find(
      (candidate) => candidate.dataset.sectionId === saved.section_id
    );
    if (button) showResumePrompt(saved, button);
  }

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;

    const termButton = target.closest(".term-play");
    if (termButton) {
      const term = termButton.closest(".term");
      const source = termButton.dataset.src;
      if (!source || source === "unavailable") return;
      setPlaylist([source], {
        label: termButton.dataset.label || term?.querySelector("h2")?.textContent,
        sectionId: term?.dataset.section || null,
        kind: "term",
      });
      return;
    }

    const chapterButton = target.closest(".play[data-section-id]");
    if (chapterButton) {
      const playlist = parsePlaylist(chapterButton.dataset.srcs);
      if (!playlist.length) return;
      setPlaylist(playlist, {
        label: chapterButton.dataset.label,
        sectionId: chapterButton.dataset.sectionId,
        kind: "chapter",
      });
    }
  });

  audio.addEventListener("loadedmetadata", updateSeek);
  audio.addEventListener("timeupdate", () => {
    updateSeek();
    saveProgress(false);
  });
  audio.addEventListener("ended", () => {
    if (state.index + 1 < state.playlist.length) {
      loadIndex(state.index + 1);
    } else {
      updateControls();
      saveProgress(true);
    }
  });
  audio.addEventListener("play", () => {
    updateControls();
    updateMediaSession();
  });
  audio.addEventListener("pause", () => {
    updateControls();
    updateMediaSession();
    saveProgress(true);
  });
  audio.addEventListener("error", () => {
    updateControls();
  });

  if ("mediaSession" in navigator) {
    try {
      navigator.mediaSession.setActionHandler("play", () => {
        audio.play().catch(() => {});
      });
      navigator.mediaSession.setActionHandler("pause", () => {
        audio.pause();
      });
      navigator.mediaSession.setActionHandler("previoustrack", playPrevious);
      navigator.mediaSession.setActionHandler("nexttrack", playNext);
      navigator.mediaSession.setActionHandler("seekbackward", (details) => {
        audio.currentTime = Math.max(
          0,
          (audio.currentTime || 0) - (details.seekOffset || 15)
        );
      });
      navigator.mediaSession.setActionHandler("seekforward", (details) => {
        audio.currentTime = Math.min(
          Number.isFinite(audio.duration) ? audio.duration : Infinity,
          (audio.currentTime || 0) + (details.seekOffset || 15)
        );
      });
      navigator.mediaSession.setActionHandler("seekto", (details) => {
        if (typeof details.seekTime === "number") {
          audio.currentTime = details.seekTime;
        }
      });
    } catch (_error) {
      // Browsers may not implement every action; keep the page usable.
    }
  }

  window.addEventListener("pagehide", () => saveProgress(true));
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") saveProgress(true);
  });

  buildPlayer();
  restoreProgress();
})();
