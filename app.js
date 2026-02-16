import { upload } from "https://esm.sh/@vercel/blob/client";

const form = document.getElementById("upload-form");
const fileInput = document.getElementById("zip-file");
const fileMeta = document.getElementById("file-meta");
const statusEl = document.getElementById("status");
const resultBox = document.getElementById("result");
const resultToken = document.getElementById("result-token");
const submitBtn = document.getElementById("submit-btn");
const isLocalFile = window.location.protocol === "file:";
const apiUrl = isLocalFile ? "http://localhost:8000/api/decode" : "/api/decode";

const setStatus = (message, tone = "muted") => {
  statusEl.textContent = message;
  statusEl.dataset.tone = tone;
};

const resetResult = () => {
  resultBox.hidden = true;
  resultToken.textContent = "";
};

if (isLocalFile) {
  setStatus("Local mode: start the server with python local_server.py");
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) {
    fileMeta.textContent = "No file selected";
    return;
  }
  fileMeta.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
  resetResult();
  setStatus("Ready to decode.");
});

const uploadViaBlob = async (file) => {
  const blob = await upload(file.name, file, {
    access: "public",
    handleUploadUrl: "/api/upload",
    contentType: "application/zip",
  });
  return blob.url;
};

const decodeWithUrl = async (fileUrl) => {
  const response = await fetch(apiUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ file_url: fileUrl }),
  });
  return response;
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    setStatus("Please select a zip file first.");
    return;
  }

  submitBtn.disabled = true;
  resetResult();
  setStatus("Uploading and decoding...", "busy");

  const formData = new FormData();
  formData.append("file", file);

  try {
    let response = null;
    if (isLocalFile) {
      response = await fetch(apiUrl, {
        method: "POST",
        body: formData,
      });
    } else {
      const blobUrl = await uploadViaBlob(file);
      response = await decodeWithUrl(blobUrl);
    }

    const rawText = await response.text();
    let payload = null;
    try {
      payload = rawText ? JSON.parse(rawText) : null;
    } catch (parseError) {
      if (!response.ok) {
        throw new Error(rawText || "Decode failed.");
      }
      throw new Error("Unexpected response from server.");
    }

    if (!response.ok) {
      throw new Error((payload && payload.error) || "Decode failed.");
    }

    resultToken.textContent = (payload && payload.decoded_token) || "";
    resultBox.hidden = false;
    setStatus("Decoded successfully.");
  } catch (error) {
    setStatus(error.message || "Something went wrong.");
  } finally {
    submitBtn.disabled = false;
  }
});
