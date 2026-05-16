import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shiny import App, ui, render
from pathlib import Path
from detector import analyze_media_concurrently
from upload_ui import upload_section

app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.link(rel="stylesheet", href="style.css"),
        ui.tags.link(rel="preconnect", href="https://fonts.googleapis.com"),
        ui.tags.link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600&display=swap"),
    ),

    # ── HERO ──────────────────────────────────────────────
    ui.div(
        ui.div(
            ui.tags.div(ui.HTML("◈"), class_="logo-icon"),
            ui.h1("AI Generated Media Detector", class_="hero-title"),
            ui.p("DETECT · ANALYSE · VERIFY", class_="hero-sub"),
            ui.div(
                ui.tags.span("POWERED BY", class_="badge-label"),
                ui.tags.span("HuggingFace  ·  Metadata Forensics  ·  Neural Analysis", class_="badge-apis"),
                class_="api-badge"
            ),
            class_="hero-inner"
        ),
        class_="hero-section"
    ),

    # ── MAIN CONTAINER ────────────────────────────────────
    ui.div(
        upload_section(),
        ui.output_ui("analysis_ui"),
        class_="main-container"
    ),

    # ── FOOTER ────────────────────────────────────────────
    ui.div(
        ui.p("AI Generated Media Detector · Built with Python Shiny · For portfolio & research use"),
        ui.p("⚠ Results are indicative. Accuracy depends on image quality and type.", class_="footer-note"),
        class_="footer"
    )
)


def server(input, output, session):

    @output
    @render.ui
    async def analysis_ui():

        file = input.file_upload()

        if not file:
            return ui.div(
                ui.div(
                    ui.HTML("🛡️"),
                    ui.p("Upload an image or video to begin analysis"),
                    class_="empty-state"
                ),
                class_="empty-wrapper"
            )

        file_info = file[0]
        filepath  = file_info["datapath"]
        filename  = file_info["name"]
        ext       = Path(filename).suffix.lower()

        # ── CALL ALL 3 APIs CONCURRENTLY ──────────────────
        analysis_data = await analyze_media_concurrently(filepath, ext)

        score   = analysis_data["overall_score"]
        details = analysis_data["details"]
        errors  = analysis_data.get("errors", {})

        # ── 3-STATE VERDICT ───────────────────────────────
        # HIGH   > 70% → AI Detected (red)
        # MEDIUM 45-70% → Inconclusive (orange)
        # LOW    < 45% → Authentic (green)
        if score > 70:
            result_text  = "⚠️  AI / SYNTHETIC MEDIA DETECTED"
            arc_color    = "#ff3d6b"
            arc_class    = "arc-danger"
            result_class = "result-danger"
        elif score > 45:
            result_text  = "🔍  INCONCLUSIVE — MANUAL REVIEW SUGGESTED"
            arc_color    = "#f5a623"
            arc_class    = "arc-warn"
            result_class = "result-warn"
        else:
            result_text  = "✅  AUTHENTIC MEDIA"
            arc_color    = "#00ffb2"
            arc_class    = "arc-safe"
            result_class = "result-safe"

        # ── MEDIA PREVIEW ─────────────────────────────────
        if ext in [".jpg", ".jpeg", ".png", ".webp"]:
            import base64
            with open(filepath, "rb") as img_file:
                b64 = base64.b64encode(img_file.read()).decode("utf-8")
            mime    = "image/jpeg" if ext in [".jpg", ".jpeg"] else f"image/{ext[1:]}"
            preview = ui.tags.img(
                src=f"data:{mime};base64,{b64}",
                class_="preview-image"
            )
        elif ext in [".mp4", ".mov", ".avi"]:
            import base64
            with open(filepath, "rb") as vid_file:
                b64 = base64.b64encode(vid_file.read()).decode("utf-8")
            preview = ui.tags.video(
                ui.tags.source(
                    src=f"data:video/mp4;base64,{b64}",
                    type="video/mp4"
                ),
                controls=True,
                class_="preview-video"
            )
        else:
            preview = ui.p("Preview not supported for this file type.")

        # ── DETECTOR MINI CARDS ───────────────────────────
        def mini_card(name, key):
            d         = details.get(key, {})
            st        = d.get("status", "Error")
            cf        = d.get("confidence", 0)
            err       = errors.get(key, "")
            is_fail   = st in ["Failed", "AI-Generated", "Error"]
            dot_class = "dot-red" if is_fail else "dot-green"
            conf_disp = f"{cf}%" if not err else "N/A"
            note      = f'<span class="api-err">{err[:60]}</span>' if err else ""
            return ui.div(
                ui.div(class_=f"dot {dot_class}"),
                ui.div(
                    ui.HTML(f'<span class="mc-name">{name}</span>'),
                    ui.HTML(f'<span class="mc-status">{st}</span>'),
                    ui.HTML(f'<span class="mc-conf">{conf_disp} confidence</span>'),
                    ui.HTML(note),
                    class_="mc-text"
                ),
                class_="mini-card"
            )

        # ── SEMI-CIRCLE ARC SVG ───────────────────────────
        dash_total = 251.2
        dash_val   = (score / 100) * dash_total
        arc_svg = ui.HTML(f"""
        <div class="arc-wrap">
          <svg viewBox="0 0 200 110" class="arc-svg">
            <path d="M 10 100 A 90 90 0 0 1 190 100"
                  fill="none" stroke="#1a2035" stroke-width="14" stroke-linecap="round"/>
            <path d="M 10 100 A 90 90 0 0 1 190 100"
                  fill="none" stroke="{arc_color}" stroke-width="14"
                  stroke-linecap="round"
                  stroke-dasharray="{dash_val:.1f} {dash_total:.1f}"
                  class="arc-fill {arc_class}"/>
            <text x="100" y="90" text-anchor="middle" class="arc-score">{score}%</text>
            <text x="100" y="108" text-anchor="middle" class="arc-label">AI CONFIDENCE</text>
          </svg>
        </div>
        """)

        # ── ACCURACY NOTE ─────────────────────────────────
        accuracy_note = ui.div(
            ui.HTML("""
            <span class="accuracy-note">
              ⓘ Results are indicative. Free AI models may produce false positives
              on real photos with unusual lighting or heavy editing.
            </span>
            """),
            class_="accuracy-wrap"
        )

        return ui.div(

            # FILE INFO BAR
            ui.div(
                ui.HTML(f'<span class="fi-icon">📄</span><span class="fi-name">{filename}</span>'),
                class_="file-info-bar"
            ),

            # PREVIEW
            ui.div(
                ui.div(preview, class_="preview-inner"),
                class_="preview-box"
            ),

            # RESULT CARD
            ui.div(
                ui.h2(result_text, class_="result-heading"),
                arc_svg,

                # MINI CARDS ROW
                ui.div(
                    mini_card("DeepVision AI", "DeepVision"),
                    mini_card("Metadata Forensics", "Metadata"),
                    mini_card("Neural Analysis", "Neural"),
                    class_="mini-grid"
                ),

                accuracy_note,

                class_=f"result-card {result_class}"
            ),

            class_="output-wrap"
        )


app = App(app_ui, server, static_assets=Path(__file__).parent / "www")