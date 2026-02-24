/**
 * AetherMind 主题加载器 v3
 * - 同步暴露 window.AetherSwitchTheme (pending queue)
 * - 支持 --ds-* 深色页面变量
 * - 支持 --theme-* 亮色页面变量
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'aethermind-active-theme';
  const CACHE_KEY = 'aethermind-theme-data';
  const CACHE_TTL = 5 * 60 * 1000;

  var pendingSwitch = null;

  // 立即暴露全局函数，确保按钮点击在 async 加载完成之前也能工作
  window.AetherSwitchTheme = function (name) {
    if (window.AetherTheme) {
      window.AetherTheme.switch(name);
    } else {
      pendingSwitch = name;
      try { localStorage.setItem(STORAGE_KEY, name); } catch (_) { }
    }
  };

  // 应用主题颜色变量到 :root
  function applyColors(colors) {
    var root = document.documentElement;

    // --theme-* 变量 (亮色页面 / workspace / landing)
    var themeMap = {
      'primary': '--theme-primary',
      'secondary': '--theme-secondary',
      'bg-60': '--theme-bg-60',
      'bg-30': '--theme-bg-30',
      'bg-sidebar': '--theme-bg-sidebar',
      'border': '--theme-border',
      'accent': '--theme-accent-10',
      'accent-hover': '--theme-accent-hover',
      'accent-light': '--theme-accent-light',
      'glass-bg': '--theme-glass-bg',
    };
    for (var key in themeMap) {
      if (colors[key] !== undefined) {
        root.style.setProperty(themeMap[key], colors[key]);
      }
    }

    // --ds-* 变量 (深色页面: product_form, index_modern 等)
    var dsMap = {
      'ds-bg': '--ds-bg',
      'ds-bg-2': '--ds-bg-2',
      'ds-bg-3': '--ds-bg-3',
      'ds-text': '--ds-text',
      'ds-text-muted': '--ds-text-muted',
      'ds-accent': '--ds-accent',
      'ds-accent-2': '--ds-accent-2',
      'ds-scrollbar': '--ds-scrollbar',
    };
    for (var k in dsMap) {
      if (colors[k] !== undefined) {
        root.style.setProperty(dsMap[k], colors[k]);
      }
    }
  }

  function applyTheme(name, themeData) {
    if (!themeData || !themeData.themes) return;
    var theme = themeData.themes[name];
    if (!theme) return;
    applyColors(theme.colors);
    document.documentElement.setAttribute('data-theme', name);
    try { localStorage.setItem(STORAGE_KEY, name); } catch (_) { }
  }

  async function loadThemeData() {
    try {
      var cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        var parsed = JSON.parse(cached);
        if (Date.now() - parsed.ts < CACHE_TTL) return parsed.data;
      }
    } catch (_) { }

    var urls = ['/api/v1/theme', '/static/theme.json'];
    for (var i = 0; i < urls.length; i++) {
      try {
        var res = await fetch(urls[i], { cache: 'no-cache' });
        if (res.ok) {
          var data = await res.json();
          try { localStorage.setItem(CACHE_KEY, JSON.stringify({ data: data, ts: Date.now() })); } catch (_) { }
          return data;
        }
      } catch (_) { }
    }
    return null;
  }

  async function init() {
    var themeData = await loadThemeData();
    if (!themeData) return;

    // 优先级: pendingSwitch > localStorage > theme.json.active > default
    var stored = null;
    try { stored = localStorage.getItem(STORAGE_KEY); } catch (_) { }
    var activeName = pendingSwitch || stored || (themeData && themeData.active) || 'default';
    pendingSwitch = null;

    applyTheme(activeName, themeData);

    window.AetherTheme = {
      data: themeData,
      current: activeName,

      switch: function (name) {
        applyTheme(name, themeData);
        this.current = name;
        // 更新 workshop 按钮激活状态
        document.querySelectorAll('[data-theme-switch]').forEach(function (btn) {
          var isActive = btn.getAttribute('data-theme-switch') === name;
          btn.style.background = isActive ? 'rgba(0,0,0,0.08)' : 'transparent';
          btn.style.borderColor = isActive ? 'rgba(0,0,0,0.18)' : 'transparent';
        });
        // 同步到服务器（可选，保持跨设备一致性）
        fetch('/api/v1/theme/active', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ theme: name })
        }).catch(function() {}); // 忽略错误，不影响用户体验
      },

      getThemes: function () {
        return Object.entries(themeData.themes).map(function (entry) {
          return { id: entry[0], label: entry[1].label };
        });
      },

      reload: async function () {
        try { localStorage.removeItem(CACHE_KEY); } catch (_) { }
        var fresh = await loadThemeData();
        if (fresh) {
          this.data = fresh;
          applyTheme(this.current, fresh);
        }
      },
    };

    window.AetherSwitchTheme = function (name) {
      window.AetherTheme.switch(name);
    };

    // 初始化按钮激活状态
    window.AetherTheme.switch(activeName);

    // 监听其他标签页的主题变化（跨标签页同步）
    window.addEventListener('storage', function(e) {
      if (e.key === STORAGE_KEY && e.newValue && window.AetherTheme) {
        window.AetherTheme.switch(e.newValue);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
