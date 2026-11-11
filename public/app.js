const STATUS_LABELS = { running: "Running", success: "Success", error: "Failed" };
const REPO_RECIPES_URL = "https://github.com/evatapai/canvas-api-examples/blob/main/recipes/";
const IDLE_TEXT = "Output appears here after you run the recipe.";

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function setState(card, status, state) {
  card.dataset.state = state;
  status.textContent = STATUS_LABELS[state] || "";
}

async function runRecipe(id, card, status, output, copy, button) {
  button.disabled = true;
  copy.hidden = true;
  setState(card, status, "running");
  output.textContent = "Running...";
  try {
    const response = await fetch("/api/run/" + id, { method: "POST" });
    const body = await response.json();
    setState(card, status, response.ok ? "success" : "error");
    output.textContent = response.ok ? JSON.stringify(body.result, null, 2) : body.error;
  } catch (err) {
    setState(card, status, "error");
    output.textContent = "Could not reach the local server: " + err.message;
  } finally {
    button.disabled = false;
    copy.hidden = false;
  }
}

document.getElementById("confirm").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) event.currentTarget.close("cancel");
});

function confirmWrite(recipeTitle) {
  const dialog = document.getElementById("confirm");
  document.getElementById("confirm-recipe").textContent = recipeTitle;
  dialog.returnValue = "cancel";
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "run"), { once: true });
    dialog.showModal();
  });
}

async function copyText(text, copy) {
  try {
    await navigator.clipboard.writeText(text);
    copy.textContent = "Copied";
  } catch (err) {
    copy.textContent = "Copy failed";
  }
  setTimeout(() => { copy.textContent = "Copy"; }, 1500);
}

function cardId(recipe) {
  return "recipe-" + recipe.id;
}

function renderIndexItem(recipe) {
  const link = el("a", recipe.title);
  link.href = "#" + cardId(recipe);
  const item = el("li");
  item.append(link);
  return item;
}

function renderCard(recipe) {
  const card = el("article", null, "card");
  card.id = cardId(recipe);
  card.dataset.state = "idle";

  const button = el("button", "Run", "run");
  button.type = "button";
  const status = el("span", null, "status");
  status.setAttribute("role", "status");

  const output = el("pre", IDLE_TEXT);
  output.tabIndex = 0;
  const copy = el("button", "Copy", "copy");
  copy.type = "button";
  copy.hidden = true;
  copy.addEventListener("click", () => copyText(output.textContent, copy));
  const outputBox = el("div", null, "panel output");
  const outputHead = el("div", null, "output-head");
  outputHead.append(el("span", "Output"), copy);
  outputBox.append(outputHead, output);

  const code = el("pre", recipe.source);
  code.tabIndex = 0;
  const copyCode = el("button", "Copy", "copy");
  copyCode.type = "button";
  copyCode.addEventListener("click", () => copyText(recipe.source, copyCode));
  const codeHead = el("div", null, "output-head");
  const sourceLink = el("a", "View on GitHub", "copy");
  sourceLink.href = REPO_RECIPES_URL + encodeURIComponent(recipe.id) + ".py";
  sourceLink.target = "_blank";
  sourceLink.rel = "noopener noreferrer";
  sourceLink.setAttribute("aria-label", "View " + recipe.id + ".py on GitHub (opens in a new tab)");
  const codeActions = el("div", null, "head-actions");
  codeActions.append(sourceLink, copyCode);
  codeHead.append(el("span", "Python"), codeActions);
  const codeBox = el("div", null, "panel code-panel");
  codeBox.append(codeHead, code);
  const details = el("details");
  details.append(el("summary", "Code"), codeBox);

  button.addEventListener("click", async () => {
    if (recipe.writes && !(await confirmWrite(recipe.title))) return;
    runRecipe(recipe.id, card, status, output, copy, button);
  });

  card.append(el("p", recipe.id, "recipe-id"), el("h2", recipe.title), el("p", recipe.description, "description"));
  if (recipe.writes) card.append(el("p", "Changes data in your demo course.", "warning"));
  const actions = el("div", null, "actions");
  actions.append(button, status);
  card.append(actions, outputBox, details);
  return card;
}

async function init() {
  const container = document.getElementById("recipes");
  const response = await fetch("/api/recipes");
  const recipes = await response.json();
  container.append(...recipes.map(renderCard));
  document.getElementById("recipe-index").append(...recipes.map(renderIndexItem));
  scrollToHash();
}

// Cards render after the page loads, so jump to a #recipe-... link once they exist.
function scrollToHash() {
  const target = location.hash && document.getElementById(location.hash.slice(1));
  if (target) target.scrollIntoView();
}

init();
