import type { MetadataRoute } from "next";
import { SITE_NAME } from "../lib/site";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: SITE_NAME,
    short_name: "Image to PDF",
    description: "Convert images to high-quality PDF files online for free.",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f4ef",
    theme_color: "#172336",
    icons: [{ src: "/favicon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
