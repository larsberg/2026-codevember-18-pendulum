# 18 / Pendulum

The starter opens on a blank, warm paper-colored canvas. Run `npm run dev` in the VS Code terminal and open the local URL Vite prints. Press **H** to show the studio drawer, or open the sketch with `?ui=1`.

The HTML shell, Vite configuration, camera, and settings workflow come from `14-tension`. **Save** writes the current settings and camera to `public/settings.json` through the development API. **Reload** reads that file, and **Reset** restores the built-in defaults. The static build saves to this device.

The drawer carries forward the palette workshop, lighting, shadows, reflections, materials, bloom, tilt blur, FPS meter, and PNG export from the Shatter and Tangle studios via Tension. The scene has an empty Box3D world. Audio starts muted. **F** previews the two Strudel voices and **P** pauses or resumes the studio.

Run `npm run check` for tests and a production build.
