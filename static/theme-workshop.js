/**
 * AetherMind 主题工坊 v3
 * - 三个主题: 海岸微风 / 羊绒与栗木 / 深空暗色
 * - 使用事件委托 (无 toString hack)
 * - 依赖 theme-loader.js 的 window.AetherSwitchTheme
 */
(function () {
  'use strict';

  var THEMES = [
    {
      id: 'default',
      label: '海岸微风',
      sublabel: 'Coastal Chic',
      swatches: ['#2563eb', '#f1f5f9'],
      swatchBorders: [false, true],
    },
    {
      id: 'cashmere-chestnut',
      label: '羊绒与栗木',
      sublabel: 'Cashmere & Chestnut',
      swatches: ['#8c4632', '#f8f5f0'],
      swatchBorders: [false, true],
    },
    {
      id: 'deep-space',
      label: '深空暗色',
      sublabel: 'Deep Space Dark',
      swatches: ['#030712', '#6366f1'],
      swatchBorders: [false, false],
    },
  ];

  function swatchHTML(theme) {
    return theme.swatches.map(function (color, i) {
      var border = theme.swatchBorders[i] ? 'border:1px solid rgba(0,0,0,0.15);' : '';
      return '<div style="width:12px;height:12px;border-radius:50%;background:' + color + ';flex-shrink:0;' + border + 'box-shadow:0 1px 3px rgba(0,0,0,0.1);"></div>';
    }).join('');
  }

  function buildPanel() {
    var buttonsHTML = THEMES.map(function (t) {
      return '<button data-theme-switch="' + t.id + '" ' +
        'style="width:100%;display:flex;align-items:center;justify-content:space-between;' +
        'padding:8px 10px;border-radius:8px;border:1px solid transparent;' +
        'background:transparent;cursor:pointer;transition:all 0.18s ease;font-family:inherit;outline:none;" ' +
        'title="' + t.label + '">' +
        '<div style="display:flex;flex-direction:column;align-items:flex-start;gap:1px;">' +
        '<span style="font-size:12px;font-weight:600;color:rgba(0,0,0,0.75);">' + t.label + '</span>' +
        '<span style="font-size:10px;color:rgba(0,0,0,0.4);">' + t.sublabel + '</span>' +
        '</div>' +
        '<div style="display:flex;gap:4px;align-items:center;margin-left:8px;">' +
        swatchHTML(t) +
        '</div>' +
        '</button>';
    }).join('');

    return '<div id="theme-workshop-widget" ' +
      'style="position:fixed;bottom:24px;right:24px;z-index:10000;' +
      'background:rgba(255,255,255,0.97);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);' +
      'border-radius:16px;padding:14px 14px 12px;' +
      'box-shadow:0 8px 40px rgba(0,0,0,0.1),0 0 0 1px rgba(0,0,0,0.06);' +
      'width:240px;display:flex;flex-direction:column;' +
      'transition:transform 0.45s cubic-bezier(0.34,1.56,0.64,1),opacity 0.3s ease;' +
      'transform:translateY(0);opacity:1;' +
      'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;">' +

      // header
      '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">' +
      '<div style="display:flex;align-items:center;gap:7px;">' +
      '<span style="font-size:16px;line-height:1;"><iconify-icon icon="solar:palette-bold" style="color: rgb(var(--theme-accent-10));"></iconify-icon></span>' +
      '<span style="font-size:13px;font-weight:700;color:rgba(0,0,0,0.78);">主题工坊</span>' +
      '</div>' +
      '<button id="theme-workshop-close" ' +
      'style="background:none;border:none;cursor:pointer;color:rgba(0,0,0,0.3);font-size:20px;line-height:1;padding:0 2px;transition:color 0.15s;" ' +
      'onmouseover="this.style.color=\'rgba(0,0,0,0.6)\'" ' +
      'onmouseout="this.style.color=\'rgba(0,0,0,0.3)\'" ' +
      'title="隐藏">×</button>' +
      '</div>' +

      // buttons
      '<div style="display:flex;flex-direction:column;gap:3px;">' +
      buttonsHTML +
      '</div>' +
      '</div>' +

      // floating toggle
      '<button id="theme-toggle-widget" ' +
      'style="position:fixed;bottom:24px;right:24px;z-index:9999;' +
      'width:44px;height:44px;border-radius:50%;' +
      'background:rgba(255,255,255,0.97);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);' +
      'border:1px solid rgba(0,0,0,0.08);' +
      'box-shadow:0 4px 20px rgba(0,0,0,0.12);' +
      'cursor:pointer;display:flex;align-items:center;justify-content:center;' +
      'transition:transform 0.45s cubic-bezier(0.34,1.56,0.64,1),opacity 0.3s ease;' +
      'transform:translateY(200%);opacity:0;font-size:20px;" ' +
      'title="打开主题工坊"><iconify-icon icon="solar:palette-round-linear"></iconify-icon></button>';
  }

  function wireEvents(container) {
    var panel = container.querySelector('#theme-workshop-widget');
    var toggle = container.querySelector('#theme-toggle-widget');
    var close = container.querySelector('#theme-workshop-close');

    close.addEventListener('click', function () {
      panel.style.transform = 'translateY(200%)';
      panel.style.opacity = '0';
      toggle.style.transform = 'translateY(0)';
      toggle.style.opacity = '1';
    });

    toggle.addEventListener('click', function () {
      panel.style.transform = 'translateY(0)';
      panel.style.opacity = '1';
      toggle.style.transform = 'translateY(200%)';
      toggle.style.opacity = '0';
    });

    // 事件委托 - 主题切换
    container.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-theme-switch]');
      if (!btn) return;
      var name = btn.getAttribute('data-theme-switch');

      // 更新所有按钮的激活状态
      container.querySelectorAll('[data-theme-switch]').forEach(function (b) {
        var isActive = b.getAttribute('data-theme-switch') === name;
        b.style.background = isActive ? 'rgba(0,0,0,0.08)' : 'transparent';
        b.style.borderColor = isActive ? 'rgba(0,0,0,0.18)' : 'transparent';
        b.dataset.active = isActive ? '1' : '0';
      });

      if (typeof window.AetherSwitchTheme === 'function') {
        window.AetherSwitchTheme(name);
      } else if (window.AetherTheme) {
        window.AetherTheme.switch(name);
      } else {
        document.documentElement.setAttribute('data-theme', name);
        try { localStorage.setItem('aethermind-active-theme', name); } catch (_) { }
      }
    });

    // hover 效果
    container.querySelectorAll('[data-theme-switch]').forEach(function (btn) {
      btn.addEventListener('mouseenter', function () {
        this.style.background = 'rgba(0,0,0,0.04)';
        this.style.borderColor = 'rgba(0,0,0,0.08)';
      });
      btn.addEventListener('mouseleave', function () {
        var isActive = this.dataset.active === '1';
        if (!isActive) {
          this.style.background = 'transparent';
          this.style.borderColor = 'transparent';
        }
      });
    });
  }

  function injectPanel() {
    if (document.getElementById('theme-workshop-widget')) return;
    var container = document.createElement('div');
    container.innerHTML = buildPanel();
    document.body.appendChild(container);
    wireEvents(container);

    // 初始化按钮激活状态
    setTimeout(function () {
      var currentTheme = localStorage.getItem('aethermind-active-theme') || 'default';
      container.querySelectorAll('[data-theme-switch]').forEach(function (btn) {
        var isActive = btn.getAttribute('data-theme-switch') === currentTheme;
        btn.style.background = isActive ? 'rgba(0,0,0,0.08)' : 'transparent';
        btn.style.borderColor = isActive ? 'rgba(0,0,0,0.18)' : 'transparent';
        btn.dataset.active = isActive ? '1' : '0';
      });
    }, 100);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectPanel);
  } else {
    injectPanel();
  }
})();
