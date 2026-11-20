# 18 / Pendulum

A white mechanical metronome stands at the center of a petrol-blue cyclorama. Each Strudel click lands at the end of a swing and cuts the furniture, lights and camera together. A 55-inch television floats in a different position in each of the nine compositions. Cyan and blue light spill onto a mustard sofa. An amber picture lights a breakfast table with two place settings and an inverted chair. The screen turns across a loaded bookcase, then hovers low beside a record player. The next five clicks take in a row of rotary phones, a billiard table ready for the break, a conservatory under a suspended grow light, a pair of front-loading washers, and a channel-stitched daybed. The ninth click returns to the parlor.

Run `npm run dev` in the VS Code terminal and open the address Vite prints. **M** enables the sound after a user gesture. **P** pauses the beat and **H** opens the studio drawer. The Audio tab's tempo sets the click, pitched accompaniment and pendulum speed. Reset starts the sequence muted at 84 BPM.

## Blender

Open [18-pendulum.blend](blender/18-pendulum.blend). The nine numbered scenes share the same stage mesh and instrument collection. The metronome measures 21 cm. Furniture uses the catalog dimensions. Each numbered scene has an editable camera and focus point. Move the camera to choose the angle, move the focus point to compose the shot, and change the lens for coverage. The parlor, billiards and daybed shots export the extent of their furniture so the whole arrangement fits on narrow screens. The other shots keep the metronome and television in frame and allow furniture at the edges to crop.

Move or rotate the **Floating television** parent in a shot to aim its light. The picture and its two rectangular emitters follow the housing. Each emitter takes the color of its half of the test card. The player varies their brightness against the pendulum beat, including when the sound is muted.

To export edits from the saved Blender file, run the following from the sketch directory with Blender 5.3.

```sh
blender -b blender/18-pendulum.blend --python-exit-code 1 --python blender/export.py
```

The export writes the instrument, stage, nine furniture groups, and camera and light data into `public/models/`. The Three.js player preloads these assets before starting the beat. To regenerate the Blender file from the original catalog downloads and modeled geometry, run `blender -b --factory-startup --python-exit-code 1 --python blender/build.py`. Model credits ship with the sketch. [Asset credits](public/models/CREDITS.md)

## Studio

The shell, Box3D world, orbit camera, palette workshop, Strudel voices and settings API come from `14-tension`. Its lighting, shadows, material controls, bloom, focus, FPS and PNG export come from the Shatter and Tangle studios. Box3D drives the kinematic reed. Strudel schedules a dry alternating click and an eight-beat accompaniment against the same transport that drives the cuts.

Camera edits adjust the framing across all shots. Save stores the settings and current beat position in `public/settings.json` during development. Reload restores the view and beat phase. Reset returns to the opening composition. Static builds save to the device.

Run `npm run check` for tests and a production build.
