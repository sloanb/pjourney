"""Regression tests for CameraFormModal.

Covers the Select.BLANK → Select.NULL breakage introduced by Textual 8:
  Select.BLANK was the "no selection" sentinel in older Textual versions.
  In Textual 8 it became a plain bool (False), causing InvalidSelectValueError
  when passed as the `value` to the sensor-size Select widget.
"""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label, Select

from pjourney.db.models import Camera, User
from pjourney.screens.cameras import CameraFormModal


class CameraFormTestApp(App):
    """Minimal host app for exercising CameraFormModal."""

    def __init__(self, camera: Camera | None = None) -> None:
        super().__init__()
        self._camera = camera
        self.dismissed_camera: Camera | None = None
        self.dismissed_called: bool = False
        # CameraFormModal.save() accesses self.app.current_user.id
        self.current_user = User(id=1, username="test")

    def compose(self) -> ComposeResult:
        yield Label("host")

    async def show_form(self) -> None:
        def on_dismiss(camera: Camera | None) -> None:
            self.dismissed_called = True
            self.dismissed_camera = camera

        await self.push_screen(CameraFormModal(self._camera), on_dismiss)


class TestCameraFormModalOpens:
    """Verify the modal renders without crashing for all camera configurations."""

    async def test_film_camera_no_sensor_size_does_not_crash(self):
        """Regression: editing a film camera (sensor_size=None) must not raise
        InvalidSelectValueError from passing Select.BLANK (False) as value."""
        camera = Camera(
            id=1, user_id=1, name="Leica M3", make="Leica",
            model="M3", camera_type="film", sensor_size=None,
        )
        app = CameraFormTestApp(camera)
        async with app.run_test() as pilot:
            await app.show_form()
            assert app.is_running

    async def test_digital_camera_with_sensor_size_does_not_crash(self):
        """Editing a digital camera that already has a sensor_size should work."""
        camera = Camera(
            id=2, user_id=1, name="Sony A7", make="Sony",
            model="A7", camera_type="digital", sensor_size="full_frame",
        )
        app = CameraFormTestApp(camera)
        async with app.run_test() as pilot:
            await app.show_form()
            assert app.is_running

    async def test_digital_camera_no_sensor_size_does_not_crash(self):
        """Editing a digital camera with sensor_size=None should work too."""
        camera = Camera(
            id=3, user_id=1, name="Fuji X-T5", make="Fuji",
            model="X-T5", camera_type="digital", sensor_size=None,
        )
        app = CameraFormTestApp(camera)
        async with app.run_test() as pilot:
            await app.show_form()
            assert app.is_running

    async def test_new_camera_form_does_not_crash(self):
        """Opening the add-camera modal (no existing camera) should work."""
        app = CameraFormTestApp(None)
        async with app.run_test() as pilot:
            await app.show_form()
            assert app.is_running


class TestCameraFormModalSensorSelect:
    """Verify the sensor-size Select widget holds the correct value after mount."""

    async def test_film_camera_sensor_select_is_null(self):
        """Film camera: sensor_size Select must show Select.NULL, not False."""
        camera = Camera(
            id=1, user_id=1, name="Leica M3", make="Leica",
            model="M3", camera_type="film", sensor_size=None,
        )
        app = CameraFormTestApp(camera)
        async with app.run_test() as pilot:
            await app.show_form()
            sensor_select = app.screen.query_one("#sensor_size", Select)
            assert sensor_select.value is Select.NULL

    async def test_digital_camera_sensor_select_shows_value(self):
        """Digital camera: sensor_size Select must reflect the stored value."""
        camera = Camera(
            id=2, user_id=1, name="Sony A7", make="Sony",
            model="A7", camera_type="digital", sensor_size="full_frame",
        )
        app = CameraFormTestApp(camera)
        async with app.run_test() as pilot:
            await app.show_form()
            sensor_select = app.screen.query_one("#sensor_size", Select)
            assert sensor_select.value == "full_frame"


class TestCameraFormModalSave:
    """Verify the save path converts Select.NULL back to None correctly."""

    async def test_saving_film_camera_yields_none_sensor_size(self):
        """When sensor_size is not selected, saved camera must have sensor_size=None."""
        from textual.widgets import Button

        camera = Camera(
            id=1, user_id=1, name="Leica M3", make="Leica",
            model="M3", camera_type="film", sensor_size=None,
        )
        app = CameraFormTestApp(camera)
        async with app.run_test() as pilot:
            await app.show_form()
            # Use Button.press() to avoid OutOfBounds from a tall modal form.
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_camera is not None
        assert app.dismissed_camera.sensor_size is None

    async def test_saving_digital_camera_preserves_sensor_size(self):
        """Saving a digital camera with a sensor size must preserve that value."""
        from textual.widgets import Button

        camera = Camera(
            id=2, user_id=1, name="Sony A7", make="Sony",
            model="A7", camera_type="digital", sensor_size="full_frame",
        )
        app = CameraFormTestApp(camera)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#save-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_camera is not None
        assert app.dismissed_camera.sensor_size == "full_frame"

    async def test_cancel_dismisses_none(self):
        """Cancel must dismiss with None regardless of camera state."""
        from textual.widgets import Button

        camera = Camera(
            id=1, user_id=1, name="Leica M3", make="Leica",
            model="M3", camera_type="film", sensor_size=None,
        )
        app = CameraFormTestApp(camera)
        async with app.run_test() as pilot:
            await app.show_form()
            app.screen.query_one("#cancel-btn", Button).press()
            await pilot.pause()
        assert app.dismissed_called
        assert app.dismissed_camera is None
