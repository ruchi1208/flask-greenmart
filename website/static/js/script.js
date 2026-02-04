const counters = document.querySelectorAll('.counter-number');
    let started = false; 

    function startCounter() {
        counters.forEach(counter => {
            const target = +counter.getAttribute('data-target');
            const duration = 2000;
            const step = target / (duration / 16);

            let count = 0;

            function update() {
                count += step;
                if (count < target) {
                    counter.innerText = Math.floor(count);
                    requestAnimationFrame(update);
                } else {
                    counter.innerText = target.toLocaleString() + "+";
                }
            }
            update();
        });
    }

    window.addEventListener('scroll', () => {
        const section = document.querySelector('.stats-wrapper');
        const position = section.getBoundingClientRect().top;

        if (position < window.innerHeight && !started) {
            startCounter();
            started = true;
        }
    });

    // Bootstrap form validation
(function () {
  'use strict'
  var forms = document.querySelectorAll('.needs-validation')
  Array.prototype.slice.call(forms).forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!form.checkValidity()) {
        event.preventDefault()
        event.stopPropagation()
      }
      form.classList.add('was-validated')
    }, false)
  })
})()

const searchInput = document.querySelector('.search-box input');
searchInput.addEventListener('input', async () => {
    const query = searchInput.value;
    if (query.length > 1) {
        const response = await fetch(`/api/search_suggestions?q=${query}`);
        const suggestions = await response.json();
        console.log(suggestions); // Show dropdown or autocomplete list
    }
});


const input = document.getElementById("searchInput");
const resultsBox = document.getElementById("searchResults");

input.addEventListener("keyup", function () {
    let q = this.value.trim();

    if (q.length === 0) {
        resultsBox.innerHTML = "";
        return;
    }

    fetch(`/live-search?q=${q}`)
        .then(res => res.json())
        .then(data => {
            resultsBox.innerHTML = "";

            data.forEach(p => {
                resultsBox.innerHTML += `
                    <div class="search-item">
                        <img src="/static/images/${p.image}" width="40">
                        <a href="/product/${p.id}">${p.name}</a>
                        <span>₹${p.price}</span>
                    </div>
                `;
            });
        });
});



function goHome(){
  window.location.href = "/";
}

