(function () {
  try {
    var list = document.querySelector("ol.dd-choices");
    var qEl = document.querySelector(".dd-question");
    if (!list || !qEl) return;
    var items = Array.prototype.slice.call(list.children);
    var n = items.length;
    if (n < 2) return;
    var key = "deckdock-mcq:" + qEl.textContent;
    var reveal = !!document.querySelector(".dd-back");

    function valid(o) {
      if (!Array.isArray(o) || o.length !== n) return false;
      for (var i = 0; i < n; i++) if (o.indexOf(i) === -1) return false;
      return true;
    }
    function load() {
      try {
        var o = JSON.parse(window.sessionStorage.getItem(key));
        return valid(o) ? o : null;
      } catch (e) {
        return null;
      }
    }
    function save(o) {
      try {
        window.sessionStorage.setItem(key, JSON.stringify(o));
        return true;
      } catch (e) {
        return false;
      }
    }
    function apply(o) {
      for (var i = 0; i < o.length; i++) list.appendChild(items[o[i]]);
    }

    var order = null;
    if (reveal) {
      order = load();
    } else {
      var o = [];
      for (var i = 0; i < n; i++) o.push(i);
      for (var j = n - 1; j > 0; j--) {
        var k = Math.floor(Math.random() * (j + 1));
        var t = o[j];
        o[j] = o[k];
        o[k] = t;
      }
      // Only shuffle when the order can be replayed on the back.
      if (save(o)) order = o;
    }
    if (order) apply(order);

    if (reveal) {
      for (var m = 0; m < n; m++) {
        if (items[m].getAttribute("data-correct") === "1") items[m].className += " dd-correct";
      }
    }
  } catch (e) {
    /* keep the original order */
  }
})();
