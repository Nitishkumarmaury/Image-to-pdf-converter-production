import { ImageResponse } from "next/og";

export const alt = "Image to PDF Converter — Free Online Tool";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "#f5f4ef",
          color: "#172336",
          display: "flex",
          flexDirection: "column",
          height: "100%",
          justifyContent: "center",
          padding: "76px",
          position: "relative",
          width: "100%",
        }}
      >
        <div style={{ color: "#7164ca", display: "flex", fontSize: 28, fontWeight: 700, letterSpacing: 4, textTransform: "uppercase" }}>Free online tool</div>
        <div style={{ display: "flex", fontSize: 86, fontWeight: 800, letterSpacing: -5, lineHeight: 1.05, marginTop: 24 }}>Image to PDF</div>
        <div style={{ color: "#7164ca", display: "flex", fontFamily: "serif", fontSize: 86, fontStyle: "italic", letterSpacing: -5, lineHeight: 1.05 }}>Converter</div>
        <div style={{ color: "#657087", display: "flex", fontSize: 30, marginTop: 36 }}>Merge images. Set the layout. Download your PDF.</div>
        <div style={{ background: "#d8ff50", borderRadius: 44, bottom: 66, display: "flex", fontSize: 24, fontWeight: 700, padding: "16px 25px", position: "absolute", right: 76 }}>No signup required</div>
      </div>
    ),
    { ...size },
  );
}
