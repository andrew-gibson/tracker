import fetch_recipies from "fetch-recipies";
import  {ui_state} from "d3-ui";

document.body.addEventListener('htmx:configRequest', (event) => {
  event.detail.headers['X-CSRFToken'] = fetch_recipies.csrf_token;
});

const setClipboard = (text) => {
    const type = "text/plain";
    const blob = new Blob([text], { type });
    const data = [new ClipboardItem({ [type]: blob })];
    navigator.clipboard.write(data);
};

