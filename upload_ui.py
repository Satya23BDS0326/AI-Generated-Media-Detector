from shiny import ui

def upload_section():
    return ui.div(
        ui.div(
            ui.HTML("""
            <div class="upload-icon">⬆</div>
            <div class="upload-title">DROP YOUR MEDIA HERE</div>
            <div class="upload-hint">Supports JPG · PNG · WEBP · MP4 · MOV · AVI</div>
            """),
            ui.input_file(
                "file_upload",
                label=None,
                accept=[".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi"],
                multiple=False,
            ),
            class_="upload-inner"
        ),
        class_="upload-card"
    )