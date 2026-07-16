const addBtn = document.getElementById('addBtn')
const closeBtn = document.getElementById('closeBtn')
const popover = document.getElementById('popover')

addBtn.addEventListener('click', function() {
    popover.classList.add('active')
})

closeBtn.addEventListener('click', function() {
    popover.classList.remove('active')
})

