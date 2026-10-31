document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('documentForm');
  if (!form) return;

  const typeInput = document.getElementById('docTypeInput');
  const contractSection = document.getElementById('contractSection');
  const currencySelect = document.getElementById('currencySelect');
  const total = document.getElementById('documentTotal');
  const submitButton = document.getElementById('submitBtn');
  const customServicesList = document.getElementById('customServicesList');
  const currencySymbols = { RWF: 'RWF', USD: '$' };

  function formatMoney(value) {
    const number = Number(value) || 0;
    const formatted = new Intl.NumberFormat(undefined, {
      minimumFractionDigits: currencySelect.value === 'USD' ? 2 : 0,
      maximumFractionDigits: 2
    }).format(number);
    return currencySelect.value === 'USD'
      ? '$' + formatted
      : 'RWF ' + formatted;
  }

  function updateTotal() {
    let sum = 0;
    ['include_hosting', 'include_domain', 'include_ssl'].forEach(function (name) {
      const checkbox = form.elements[name];
      if (checkbox.checked) {
        const priceName = name === 'include_hosting'
          ? 'hosting_fee'
          : name === 'include_domain' ? 'domain_fee' : 'ssl_fee';
        sum += Number(form.elements[priceName].value) || 0;
      }
    });
    customServicesList.querySelectorAll('input[name="custom_service_price[]"]').forEach(function (input) {
      sum += Number(input.value) || 0;
    });
    total.textContent = formatMoney(sum);
    document.querySelectorAll('.currency-code').forEach(function (element) {
      element.textContent = currencySymbols[currencySelect.value];
    });
    customServicesList.querySelectorAll('.custom-price-label').forEach(function (label) {
      label.textContent = 'Price (' + currencySelect.value + ')';
    });
  }

  function updateService(checkbox) {
    const fields = document.querySelector('[data-service-fields="' + checkbox.name + '"]');
    const option = checkbox.closest('.service-option');
    fields.classList.toggle('is-disabled', !checkbox.checked);
    fields.querySelectorAll('input').forEach(function (input) {
      input.disabled = !checkbox.checked;
    });
    option.classList.toggle('is-selected', checkbox.checked);
    updateTotal();
  }

  document.querySelectorAll('.service-toggle input[type="checkbox"]').forEach(function (checkbox) {
    checkbox.addEventListener('change', function () { updateService(checkbox); });
    updateService(checkbox);
  });

  document.querySelectorAll('.switch-btn').forEach(function (button) {
    button.addEventListener('click', function () {
      document.querySelectorAll('.switch-btn').forEach(function (item) {
        const selected = item === button;
        item.classList.toggle('active', selected);
        item.setAttribute('aria-pressed', selected ? 'true' : 'false');
      });
      typeInput.value = button.dataset.type;
      const includeContract = button.dataset.type !== 'invoice';
      contractSection.hidden = !includeContract;
      document.getElementById('docTitle').value = {
        invoice: 'Service Invoice',
        contract: 'Service Agreement',
        both: 'Service Invoice & Agreement'
      }[button.dataset.type];
    });
  });

  currencySelect.addEventListener('change', updateTotal);
  form.querySelectorAll('input[name="hosting_fee"], input[name="domain_fee"], input[name="ssl_fee"]')
    .forEach(function (input) {
      input.addEventListener('input', updateTotal);
    });

  document.getElementById('addCustomService').addEventListener('click', function () {
    const row = document.createElement('div');
    row.className = 'custom-service-row';

    const fields = [
      { label: 'Service name', name: 'custom_service_name[]', placeholder: 'e.g. Website design' },
      { label: 'Description', name: 'custom_service_description[]', placeholder: 'What is included' },
      { label: 'Price (' + currencySelect.value + ')', name: 'custom_service_price[]', placeholder: '0.00', type: 'number' }
    ];
    fields.forEach(function (field) {
      const wrapper = document.createElement('div');
      wrapper.className = 'field';
      const label = document.createElement('label');
      label.textContent = field.label;
      if (field.name === 'custom_service_price[]') {
        label.className = 'custom-price-label';
        label.textContent = 'Price (' + currencySelect.value + ')';
      }
      const input = document.createElement('input');
      input.type = field.type || 'text';
      input.name = field.name;
      input.placeholder = field.placeholder;
      if (field.type === 'number') {
        input.min = '0';
        input.step = '0.01';
        input.inputMode = 'decimal';
        input.addEventListener('input', updateTotal);
      }
      wrapper.append(label, input);
      row.appendChild(wrapper);
    });

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'btn btn-secondary remove-service-btn';
    remove.textContent = 'Remove';
    remove.addEventListener('click', function () {
      row.remove();
      updateTotal();
    });
    row.appendChild(remove);
    customServicesList.appendChild(row);
  });

  ['agencySignature', 'agencyStamp'].forEach(function (id) {
    const input = document.getElementById(id);
    if (!input) return;
    input.addEventListener('change', function () {
      const name = input.files.length ? input.files[0].name : 'No file selected';
      const display = document.querySelector('[data-file-name="' + id + '"]');
      display.textContent = name;
      display.classList.toggle('has-file', input.files.length > 0);
    });
  });

  form.addEventListener('submit', function () {
    submitButton.disabled = true;
    submitButton.querySelector('span').textContent = 'Preparing your PDF...';
  });

  updateTotal();
});
