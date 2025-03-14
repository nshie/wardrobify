loadWardrobe();

document.getElementById('add-clothes-form').addEventListener('submit', (e) => {
  e.preventDefault();

  const requestBody = {
    name: document.getElementById('new-clothes-name').value,
    type: document.getElementById('new-clothes-type').value,
    image_address: document.getElementById('new-clothes-image-address').value
  }

  fetch("/api/clothes", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody)
  })
  .then(response => {
    if (response.ok) {
      loadWardrobe();
    }
  })
});

function loadWardrobe() {
  wardrobeElement = document.getElementById("wardrobe-data");

  wardrobeElement.innerHTML = 'Loading...';

  fetch("/api/clothes")
  .then(res => res.json())
  .then(data => {
    wardrobeElement.innerHTML = '';
    for (let clothing of data) {
      wardrobeElement.innerHTML += `
        <div class="clothing">
          <div>Name: ${clothing.name}</div>
          <div>Type: ${clothing.type}</div>
          <div><img src="${clothing.image_address}" width="240px" title="${clothing.name}"></div>
          <div id="edit-clothes-${clothing.id}" class="hidden">
                <h3>Edit Clothes</h3>
                <form class="edit-form">
                    <input type="text" id="edit-clothes-name-${clothing.id}" placeholder="Name" value="${clothing.name}">                    
                    <input type="text" id="edit-clothes-type-${clothing.id}" placeholder="Type" value="${clothing.type}">
                    <input type="text" id="edit-clothes-image-address-${clothing.id}" placeholder="Image Address" value="${clothing.image_address}">
                    <button type="button" id="submit-edit-clothes-${clothing.id}"
                    onclick="
                      editClothes(
                        ${clothing.id},
                        document.getElementById('edit-clothes-name-${clothing.id}').value,
                        document.getElementById('edit-clothes-type-${clothing.id}').value,
                        document.getElementById('edit-clothes-image-address-${clothing.id}').value
                      )
                    ">Submit</button>
                </form>
            </div>
          <button type="button" class="edit-button" onclick="toggleVisibility('edit-clothes-${clothing.id}')">Edit</button>
          <button type="button" class="delete-button" onclick="removeClothes(${clothing.id})">
            <img src="/static/delete.svg" width="15px" title="delete">
          </button>
        </div>
      `;

      document.getElementById(`submit-edit-clothes-${clothing.id}`).addEventListener('submit', (e) => {
        e.preventDefault();

        editClothes(
          clothing.id,
          document.getElementById(`edit-clothes-name-${clothing.id}`).value,
          document.getElementById(`edit-clothes-type-${clothing.id}`).value,
          document.getElementById(`edit-clothes-image-address-${clothing.id}`).value
        )
      });
    }
  }).catch(() => {
    sensorDataElement.innerHTML += `
      <div>Failed to load sensor data<div>
    `;
  })
}

function removeClothes(id) {
  fetch(`/api/clothes/${id}`, {
    method: 'DELETE',
  })
  .then(res => {
    if (res.ok) {
      loadWardrobe();
    }
  });
}

function editClothes(id, new_name, new_type, new_image_address) {
  const requestBody = {
    name: new_name,
    type: new_type,
    image_address: new_image_address
  }
  
  fetch(`/api/clothes/${id}`, {
    method: 'PUT',
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody)
  })
  .then(res => {
    if (res.ok) {
      loadWardrobe();
    }
  });
}

function toggleVisibility(id) {
  const element = document.getElementById(id);
  if (element.className.includes("hidden")) {
    element.className = element.className.replace("hidden", "");
  } else {
    element.className += " hidden";
  }
}