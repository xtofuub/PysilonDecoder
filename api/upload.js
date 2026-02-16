import { handleUpload } from "@vercel/blob";

const readJsonBody = (request) =>
  new Promise((resolve, reject) => {
    let data = "";
    request.on("data", (chunk) => {
      data += chunk;
    });
    request.on("end", () => {
      if (!data) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(data));
      } catch (error) {
        reject(error);
      }
    });
    request.on("error", reject);
  });

export default async function handler(request, response) {
  try {
    const body = await readJsonBody(request);
    const jsonResponse = await handleUpload({
      body,
      request,
      onBeforeGenerateToken: async () => {
        return {
          allowedContentTypes: ["application/zip"],
          maximumSizeInBytes: 150 * 1024 * 1024,
        };
      },
      onUploadCompleted: async () => {},
    });

    response.status(200).json(jsonResponse);
  } catch (error) {
    response.status(400).json({ error: error.message || "Upload failed." });
  }
}
