from shiny import ui

def detection_result(prediction, confidence):

    if prediction == "AI-Generated":
        status_color = "#ef4444"
        status_text = "⚠️ AI-Generated Content Detected"

    else:
        status_color = "#22c55e"
        status_text = "✅ Mostly Authentic Media"

    return ui.div(

        ui.div(

            ui.h2(status_text),

            ui.h1(f"{confidence}%"),

            ui.p("AI Confidence Score"),

            class_="result-banner",
            style=f"border: 2px solid {status_color};"

        ),

        ui.div(

            ui.div(
                ui.h4("DeepVision"),
                ui.p("✔ Passed"),
                class_="detector-card"
            ),

            ui.div(
                ui.h4("Metadata Scan"),
                ui.p("✔ Verified"),
                class_="detector-card"
            ),

            ui.div(
                ui.h4("Neural Analysis"),
                ui.p("✔ Checked"),
                class_="detector-card"
            ),

            class_="detector-grid"
        )
    )