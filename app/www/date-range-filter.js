(function() {
  var MONTH_LABEL = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' });
  var DATE_LABEL = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function parseDate(value) {
    if (!value) return null;
    var parts = String(value).slice(0, 10).split('-').map(Number);
    if (parts.length !== 3 || parts.some(isNaN)) return null;
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  function iso(date) {
    return date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate());
  }

  function sameDay(a, b) {
    return !!a && !!b && iso(a) === iso(b);
  }

  function clampDate(date, min, max) {
    if (!date) return null;
    if (min && date < min) return new Date(min);
    if (max && date > max) return new Date(max);
    return date;
  }

  function daysInclusive(start, end) {
    if (!start || !end) return 0;
    var ms = new Date(end.getFullYear(), end.getMonth(), end.getDate()) -
      new Date(start.getFullYear(), start.getMonth(), start.getDate());
    return Math.max(1, Math.round(ms / 86400000) + 1);
  }

  function getState(root) {
    if (root._drfState) return root._drfState;
    var from = parseDate(root.dataset.start);
    var to = parseDate(root.dataset.end);
    var min = parseDate(root.dataset.min);
    var max = parseDate(root.dataset.max);
    from = clampDate(from, min, max);
    to = clampDate(to, min, max);
    if (from && to && to < from) {
      var tmp = from;
      from = to;
      to = tmp;
    }
    root._drfState = {
      from: from,
      to: to,
      pendingFrom: from,
      pendingTo: to,
      openField: null,
      hover: null,
      min: min,
      max: max,
      view: new Date((from || to || max || new Date()).getFullYear(), (from || to || max || new Date()).getMonth(), 1)
    };
    return root._drfState;
  }

  function role(root, name) {
    return root.querySelector('[data-role="' + name + '"]');
  }

  function notifyTargets(root) {
    var state = getState(root);
    if (!state.from || !state.to) return;
    var value = [iso(state.from), iso(state.to)];
    (root.dataset.targetInputs || '').split(',').filter(Boolean).forEach(function(id) {
      if (window.Shiny && Shiny.setInputValue) {
        Shiny.setInputValue(id, value, { priority: 'event' });
      }
    });
  }

  function syncHidden(root, notify) {
    var state = getState(root);
    var startEl = document.getElementById(root.dataset.startInput);
    var endEl = document.getElementById(root.dataset.endInput);
    if (startEl && state.from) startEl.value = iso(state.from);
    if (endEl && state.to) endEl.value = iso(state.to);
    if (state.from) root.dataset.start = iso(state.from);
    if (state.to) root.dataset.end = iso(state.to);
    if (notify) notifyTargets(root);
  }

  function setOpen(root, field) {
    var state = getState(root);
    state.openField = field;
    state.pendingFrom = state.from ? new Date(state.from) : null;
    state.pendingTo = state.to ? new Date(state.to) : null;
    state.hover = null;
    var focusDate = field === 'to' ? state.pendingTo : state.pendingFrom;
    focusDate = focusDate || state.pendingFrom || state.pendingTo || state.max || new Date();
    state.view = new Date(focusDate.getFullYear(), focusDate.getMonth(), 1);
    root.classList.add('drf-open');
    render(root);
  }

  function close(root) {
    var state = getState(root);
    state.openField = null;
    state.hover = null;
    root.classList.remove('drf-open');
    render(root);
  }

  function displayDate(date) {
    return date ? DATE_LABEL.format(date) : 'Select date';
  }

  function effectiveRange(state) {
    var start = state.pendingFrom;
    var end = state.pendingTo;
    if (state.openField === 'to' && start && !end && state.hover && state.hover >= start) {
      end = state.hover;
    }
    return { start: start, end: end };
  }

  function renderDay(root, day, inMonth) {
    var state = getState(root);
    var range = effectiveRange(state);
    var disabled = (state.min && day < state.min) || (state.max && day > state.max);
    var selectedStart = sameDay(day, range.start);
    var selectedEnd = sameDay(day, range.end);
    var inRange = range.start && range.end && day > range.start && day < range.end;
    var previewEnd = state.openField === 'to' && state.hover && sameDay(day, state.hover) && !state.pendingTo;

    var cell = document.createElement('div');
    cell.className = 'drf-day-cell' + (inMonth ? '' : ' drf-day-muted');

    if (range.start && range.end) {
      if (inRange) {
        var fill = document.createElement('span');
        fill.className = 'drf-range-fill drf-range-fill-full';
        cell.appendChild(fill);
      } else if (selectedStart && !selectedEnd) {
        var startFill = document.createElement('span');
        startFill.className = 'drf-range-fill drf-range-fill-right';
        cell.appendChild(startFill);
      } else if (selectedEnd && !selectedStart) {
        var endFill = document.createElement('span');
        endFill.className = 'drf-range-fill drf-range-fill-left';
        cell.appendChild(endFill);
      }
    }

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = day.getDate();
    btn.className = 'drf-day-btn';
    btn.disabled = disabled || !inMonth;
    btn.dataset.date = iso(day);

    var today = new Date();
    if (selectedStart || selectedEnd) btn.classList.add('is-selected');
    else if (inRange) btn.classList.add('is-in-range');
    else if (sameDay(day, today)) btn.classList.add('is-today');

    if (!btn.disabled) {
      btn.addEventListener('mouseenter', function() {
        if (state.openField !== 'to' || !state.pendingFrom || state.pendingTo) return;
        var nextHover = parseDate(btn.dataset.date);
        if (sameDay(state.hover, nextHover)) return;
        state.hover = nextHover;
        render(root);
      });
      btn.addEventListener('pointerdown', function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var picked = parseDate(btn.dataset.date);
        if (state.openField === 'from') {
          state.pendingFrom = picked;
          state.pendingTo = null;
          state.openField = 'to';
        } else {
          if (state.pendingFrom && picked < state.pendingFrom) {
            state.pendingTo = state.pendingFrom;
            state.pendingFrom = picked;
          } else {
            state.pendingTo = picked;
          }
        }
        state.hover = null;
        render(root);
      });
    }

    cell.appendChild(btn);
    if (previewEnd && !selectedStart && !selectedEnd) {
      var ring = document.createElement('span');
      ring.className = 'drf-preview-ring';
      cell.appendChild(ring);
    }
    return cell;
  }

  function renderCalendar(root) {
    var state = getState(root);
    role(root, 'month-label').textContent = MONTH_LABEL.format(state.view);
    var daysEl = role(root, 'days');
    daysEl.innerHTML = '';

    var year = state.view.getFullYear();
    var month = state.view.getMonth();
    var first = new Date(year, month, 1);
    var start = new Date(year, month, 1 - first.getDay());
    for (var i = 0; i < 42; i++) {
      var day = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
      daysEl.appendChild(renderDay(root, day, day.getMonth() === month));
    }
  }

  function render(root) {
    var state = getState(root);
    var fromText = role(root, 'from-text');
    var toText = role(root, 'to-text');
    if (fromText) fromText.textContent = displayDate(state.from);
    if (toText) toText.textContent = displayDate(state.to);

    var badge = role(root, 'badge');
    if (badge) badge.textContent = daysInclusive(state.from, state.to) + 'd';

    root.querySelectorAll('.drf-datebox').forEach(function(box) {
      var active = state.openField === box.dataset.field;
      box.classList.toggle('is-active', active);
      box.setAttribute('aria-expanded', active ? 'true' : 'false');
    });
    root.querySelectorAll('.drf-pill').forEach(function(pill) {
      var field = pill.dataset.pill;
      pill.classList.toggle('is-active', state.openField === field);
      pill.classList.toggle('has-value', field === 'from' ? !!state.pendingFrom : !!state.pendingTo);
    });

    var apply = root.querySelector('[data-action="apply"]');
    if (apply) apply.disabled = !(state.pendingFrom && state.pendingTo);
    if (root.classList.contains('drf-open')) renderCalendar(root);
  }

  function initFilter(root) {
    if (root.dataset.drfReady === 'true') return;
    root.dataset.drfReady = 'true';
    getState(root);
    syncHidden(root, false);

    root.querySelectorAll('.drf-datebox').forEach(function(box) {
      box.addEventListener('click', function(ev) {
        ev.stopPropagation();
        setOpen(root, box.dataset.field);
      });
    });
    root.querySelectorAll('.drf-pill').forEach(function(pill) {
      pill.addEventListener('click', function(ev) {
        ev.stopPropagation();
        getState(root).openField = pill.dataset.pill;
        render(root);
      });
    });
    root.querySelectorAll('.drf-nav-btn').forEach(function(btn) {
      btn.addEventListener('click', function(ev) {
        ev.stopPropagation();
        var state = getState(root);
        var delta = btn.dataset.nav === 'prev' ? -1 : 1;
        state.view = new Date(state.view.getFullYear(), state.view.getMonth() + delta, 1);
        render(root);
      });
    });
    root.querySelector('[data-action="cancel"]').addEventListener('click', function(ev) {
      ev.stopPropagation();
      getState(root).pendingFrom = getState(root).from;
      getState(root).pendingTo = getState(root).to;
      close(root);
    });
    root.querySelector('[data-action="apply"]').addEventListener('click', function(ev) {
      ev.stopPropagation();
      var state = getState(root);
      if (!state.pendingFrom || !state.pendingTo) return;
      state.from = new Date(state.pendingFrom);
      state.to = new Date(state.pendingTo);
      if (state.to < state.from) {
        var tmp = state.from;
        state.from = state.to;
        state.to = tmp;
      }
      syncHidden(root, true);
      close(root);
    });
    render(root);
  }

  function initAll() {
    document.querySelectorAll('.date-range-filter').forEach(initFilter);
  }

  window._setDateRangeFilter = function(filterId, startStr, endStr, notify) {
    var root = document.querySelector('.date-range-filter[data-filter-id="' + filterId + '"]');
    if (!root) return false;
    initFilter(root);
    var state = getState(root);
    var start = clampDate(parseDate(startStr), state.min, state.max);
    var end = clampDate(parseDate(endStr), state.min, state.max);
    if (!start || !end) return false;
    if (end < start) {
      var tmp = start;
      start = end;
      end = tmp;
    }
    state.from = start;
    state.to = end;
    state.pendingFrom = start;
    state.pendingTo = end;
    state.view = new Date(start.getFullYear(), start.getMonth(), 1);
    syncHidden(root, notify !== false);
    render(root);
    return true;
  };

  document.addEventListener('mousedown', function(ev) {
    document.querySelectorAll('.date-range-filter.drf-open').forEach(function(root) {
      if (!root.contains(ev.target)) close(root);
    });
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
  if (window.jQuery) {
    jQuery(document).on('shiny:connected', initAll);
  }
})();
