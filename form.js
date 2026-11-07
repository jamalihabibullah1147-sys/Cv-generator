(function () {
  "use strict";

  var LEVELS = ["Beginner", "Intermediate", "Advanced", "Expert"];

  var SKILLS = ["Python","Java","JavaScript","TypeScript","C","C++","C#","PHP","Ruby","Go","Rust","Kotlin","Swift","Dart","R","MATLAB","SQL","HTML","CSS","Sass","Bootstrap","Tailwind CSS","React","Angular","Vue.js","Next.js","Node.js","Express.js","Django","Flask","FastAPI","Laravel","Spring Boot","ASP.NET","jQuery","Flutter","React Native","Android Development","iOS Development","MySQL","PostgreSQL","MongoDB","SQLite","Firebase","Oracle","Redis","Git","GitHub","Docker","Kubernetes","Linux","AWS","Azure","Google Cloud","CI/CD","REST API","GraphQL","Microservices","Data Structures","Algorithms","Object-Oriented Programming","Machine Learning","Deep Learning","Artificial Intelligence","Data Analysis","Data Science","Data Visualization","Pandas","NumPy","TensorFlow","PyTorch","Scikit-learn","OpenCV","NLP","Power BI","Tableau","Microsoft Excel","Microsoft Word","Microsoft PowerPoint","Google Sheets","Cyber Security","Ethical Hacking","Networking","Cloud Computing","Software Testing","Selenium","Agile / Scrum","Project Management","UI Design","UX Design","Figma","Adobe Photoshop","Adobe Illustrator","Adobe Premiere Pro","Canva","Graphic Design","Video Editing","Content Writing","Copywriting","SEO","Digital Marketing","Social Media Marketing","Email Marketing","Sales","Customer Service","Accounting","QuickBooks","Bookkeeping","Financial Analysis","Business Analysis","Leadership","Communication","Teamwork","Problem Solving","Critical Thinking","Time Management","Public Speaking","Negotiation","Teaching","Research","Technical Writing","Typing","Data Entry","Arduino","Raspberry Pi","IoT","AutoCAD","SolidWorks"];

  var LANGUAGES = ["English","Urdu","Sindhi","Punjabi","Pashto","Balochi","Saraiki","Hindi","Arabic","Persian","Turkish","Chinese (Mandarin)","Japanese","Korean","French","German","Spanish","Italian","Portuguese","Russian","Dutch","Swedish","Norwegian","Danish","Finnish","Polish","Greek","Hebrew","Bengali","Tamil","Telugu","Gujarati","Marathi","Malay","Indonesian","Thai","Vietnamese","Swahili","Ukrainian","Czech","Romanian","Hungarian"];

  /* ------------------------------------------------ searchable picker */
  function initPicker(root, items) {
    var prefix = root.dataset.prefix;
    var noun = root.dataset.noun || "Item";
    var toggle = root.querySelector(".picker-toggle");
    var panel = root.querySelector(".picker-panel");
    var input = root.querySelector(".picker-input");
    var list = root.querySelector(".picker-list");
    var chips = root.querySelector(".chips");
    var added = {};

    function addItem(name) {
      var key = name.toLowerCase();
      if (!name || added[key]) return;
      added[key] = true;

      var chip = document.createElement("div");
      chip.className = "chip";

      var label = document.createElement("span");
      label.className = "chip-name";
      label.textContent = name;

      var hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = prefix + "_name";
      hidden.value = name;

      var wrapR = document.createElement("div");
      wrapR.className = "range-wrap";
      var rng = document.createElement("input");
      rng.type = "range"; rng.min = 10; rng.max = 100; rng.step = 5; rng.value = 70;
      rng.name = prefix + "_level";
      rng.title = "How expert are you?";
      var pct = document.createElement("span");
      pct.className = "pct";
      pct.textContent = "70%";
      rng.addEventListener("input", function () { pct.textContent = rng.value + "%"; });
      wrapR.appendChild(rng);
      wrapR.appendChild(pct);

      var rm = document.createElement("button");
      rm.type = "button";
      rm.className = "chip-remove";
      rm.title = "Remove";
      rm.innerHTML = "&times;";
      rm.addEventListener("click", function () {
        delete added[key];
        chip.remove();
        render();
      });

      chip.appendChild(label);
      chip.appendChild(hidden);
      chip.appendChild(wrapR);
      chip.appendChild(rm);
      chips.appendChild(chip);

      input.value = "";
      render();
      input.focus();
    }

    function option(text, value, custom) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "opt-item" + (custom ? " custom" : "");
      b.textContent = text;
      b.addEventListener("click", function () { addItem(value); });
      return b;
    }

    function render() {
      var q = input.value.trim();
      var ql = q.toLowerCase();
      list.innerHTML = "";

      if (q && !added[ql] && !items.some(function (i) { return i.toLowerCase() === ql; })) {
        list.appendChild(option('+ Add "' + q + '" as ' + noun.toLowerCase(), q, true));
      }
      items.filter(function (i) {
        return !added[i.toLowerCase()] && i.toLowerCase().indexOf(ql) !== -1;
      }).slice(0, 80).forEach(function (i) {
        list.appendChild(option(i, i, false));
      });
      if (!list.children.length) {
        var e = document.createElement("div");
        e.className = "picker-empty";
        e.textContent = "Nothing left to add";
        list.appendChild(e);
      }
    }

    toggle.addEventListener("click", function () {
      panel.hidden = !panel.hidden;
      toggle.textContent = panel.hidden ? "+ Add " + noun : "Close list";
      if (!panel.hidden) { render(); input.focus(); }
    });
    input.addEventListener("input", render);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        var first = list.querySelector(".opt-item");
        if (first) first.click();
      }
    });
  }

  initPicker(document.getElementById("skillPicker"), SKILLS);
  initPicker(document.getElementById("languagePicker"), LANGUAGES);

  /* ------------------------------------------------ repeatable blocks */
  function repeater(btnId, tplId, boxId) {
    var btn = document.getElementById(btnId);
    var tpl = document.getElementById(tplId);
    var box = document.getElementById(boxId);

    function renumber() {
      Array.prototype.forEach.call(box.querySelectorAll(".entry"), function (e, i) {
        e.querySelector(".entry-title").textContent = e.dataset.label + " " + (i + 1);
      });
    }
    function add(focus) {
      var node = tpl.content.firstElementChild.cloneNode(true);
      node.querySelector(".entry-remove").addEventListener("click", function () {
        node.remove(); renumber();
      });
      box.appendChild(node);
      renumber();
      if (focus) node.querySelector("input, textarea").focus();
    }
    btn.addEventListener("click", function () { add(true); });
    return add;
  }

  repeater("addExp", "tplExp", "expBox");
  var addEdu = repeater("addEdu", "tplEdu", "eduBox");
  repeater("addProj", "tplProj", "projBox");
  repeater("addSocial", "tplSocial", "socialBox");
  addEdu(false); // start with one education block (can be removed)

  // "Other" platform -> show custom name field
  document.getElementById("socialBox").addEventListener("change", function (e) {
    if (e.target.classList.contains("social-type")) {
      var wrap = e.target.closest(".entry").querySelector(".social-label-wrap");
      wrap.hidden = e.target.value !== "Other";
    }
  });

  /* ------------------------------------------------ photo preview */
  var photoInput = document.getElementById("photoInput");
  var preview = document.getElementById("photoPreview");
  var placeholder = document.getElementById("photoPlaceholder");
  photoInput.addEventListener("change", function () {
    var f = photoInput.files && photoInput.files[0];
    if (!f) { preview.hidden = true; placeholder.hidden = false; return; }
    preview.src = URL.createObjectURL(f);
    preview.hidden = false;
    placeholder.hidden = true;
  });
})();