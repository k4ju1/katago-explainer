'use strict';

const english = {
  skip: 'Skip to content', navStart: 'Get started', eyebrow: 'GO LEARNING · WINDOWS APP',
  title1: 'Understand the move.', title2: 'Start here.',
  lead: 'Why this move? How will your opponent reply? Explore clear explanations and follow each continuation on the board.',
  download: 'Download for Windows', downloadMeta: 'Free beta v0.2.0-beta.2 · Windows 10 / 11 x64',
  reassurance: 'No account · Setup wizard · Desktop shortcut', sceneLabel: 'One move. Two continuations.',
  sceneNote: 'Follow the line. Understand the choices.',
  feature1: 'Understand the choice', feature1Body: "Compare your move with AI's first choice using board facts and search evidence.",
  feature2: 'Follow the continuation', feature2Body: 'Replay replies move by move, with win-rate and score changes along the line.',
  feature3: 'Connect it to Go theory', feature3Body: 'Explore kick, Shusaku kosumi, attach-and-retreat and a Mi’s Flying Dagger entry with sourced references.',
  startEyebrow: 'THREE STEPS TO YOUR FIRST REVIEW', startTitle: 'Install it like any other app.',
  step1: 'Download the installer', step1Body: 'Click the green button above and let the download finish.',
  step2: 'Complete setup', step2Body: 'Open the downloaded file, select your language and follow the setup wizard.',
  step3: 'Open and explore', step3Body: 'Use the desktop shortcut. Setup can open a sample game; choose “Explain last move”.',
  requirements: 'System requirements', requirementsBody: 'Windows 10 / 11 x64 with an OpenCL-capable graphics driver. First-time engine tuning may take a while.',
  help: 'About this beta', helpBody: 'This installer is unsigned, so Windows may show an unknown publisher. Explanations support learning and review; keep any error message if something goes wrong.',
  feedback: 'Report a problem ↗', footer: 'KataGo Explainer · An independent Go learning tool based on KaTrain and KataGo',
  release: 'Release notes', source: 'Source project'
};
const elements = [...document.querySelectorAll('[data-i18n]')];
const chinese = Object.fromEntries(elements.map(element => [element.dataset.i18n, element.textContent]));
const languageButton = document.getElementById('language');
let language = 'zh';
try { if (localStorage.getItem('kx-download-language') === 'en') language = 'en'; } catch (_) { /* Optional preference storage. */ }

function renderLanguage() {
  const dictionary = language === 'en' ? english : chinese;
  for (const element of elements) element.textContent = dictionary[element.dataset.i18n];
  document.documentElement.lang = language === 'en' ? 'en' : 'zh-CN';
  document.title = language === 'en' ? 'KataGo Explainer · Download and get started' : 'KataGo Explainer · 下载与开始使用';
  languageButton.textContent = language === 'en' ? '中文' : 'English';
  languageButton.setAttribute('aria-label', language === 'en' ? '切换为中文' : 'Switch to English');
}
languageButton.addEventListener('click', () => {
  language = language === 'zh' ? 'en' : 'zh';
  try { localStorage.setItem('kx-download-language', language); } catch (_) { /* Page also works without storage. */ }
  renderLanguage();
});
renderLanguage();
