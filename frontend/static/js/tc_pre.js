document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('tc-form');
  const submitBtn = document.getElementById('tc-submit-btn');
  const messageBox = document.getElementById('tc-message');
  const resultCard = document.getElementById('tc-result-card');
  const resultValue = document.getElementById('tc-result-value');
  const detailList = document.getElementById('tc-details');

  const showMessage = (type, text) => {
    messageBox.className = `alert alert-${type}`;
    messageBox.textContent = text;
    messageBox.classList.remove('d-none');
  };

  const hideMessage = () => {
    messageBox.classList.add('d-none');
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const contcarInput = document.getElementById('contcar-input');
    const pdosInput = document.getElementById('pdos-input');
    const contcarFile = contcarInput.files[0];
    const pdosFiles = Array.from(pdosInput.files);

    if (!contcarFile) {
      showMessage('warning', '请先选择结构文件。');
      return;
    }
    if (pdosFiles.length === 0) {
      showMessage('warning', '请至少上传一个 PDOS 文件。');
      return;
    }

    const formData = new FormData();
    formData.append('contcar', contcarFile);
    pdosFiles.forEach((file) => formData.append('pdos_files', file));

    hideMessage();
    resultCard.classList.add('d-none');
    submitBtn.disabled = true;
    submitBtn.textContent = '预测中...';

    try {
      const response = await fetch('/api/tc-predict', {
        method: 'POST',
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || payload.message || '预测失败，请稍后重试');
      }

      resultValue.textContent = `${Number(payload.predicted_tc).toFixed(2)} K`;
      detailList.innerHTML = `
        <dt class="col-6">f2</dt><dd class="col-6">${payload.f2_value}</dd>
        <dt class="col-6">dos_H_ratio</dt><dd class="col-6">${payload.dos_h_ratio}</dd>
        <dt class="col-6">dos_H_atom_bond</dt><dd class="col-6">${payload.dos_h_atom_bond}</dd>
        <dt class="col-6">⟨d(H-H)⟩</dt><dd class="col-6">${payload.bonds_mean}</dd>
        <dt class="col-6">Var(H-H)</dt><dd class="col-6">${payload.bonds_var}</dd>
      `;
      resultCard.classList.remove('d-none');
    } catch (error) {
      showMessage('danger', error.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = '开始预测';
    }
  });
});
