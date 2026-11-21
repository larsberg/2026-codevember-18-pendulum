# 18 / Pendulum

A white mechanical metronome stands at the center of a petrol-blue cyclorama. Each Strudel click lands at the end of a swing and cuts the furniture, lights and camera together. A 55-inch television floats in a different position in each of the ten compositions. Cyan and blue light spill onto a mustard sofa. An amber picture lights a clockwork orrery set between two breakfast plates. The screen turns across a loaded bookcase, then hovers low beside a record player. An overhead cut looks down on an open aluminum stepladder leading from the floor up to the front of the lacquered counter. A striped runner lies across the open floor in front of the counter. The next three shots look back through the conservatory, skim the floor beside the washers, and look over the pinball playfield and its painted backglass. The last two cuts move from Citrus, a lemon-yellow soda fountain in broad daylight, to Nocturne, a dark projection booth with a single cinema seat. The tenth click returns to the parlor from a second angle. A third pass uses the remaining cameras, and the opening view returns on click 30.

Click the sketch to hear three bars of 4/4 at 90 BPM. The metronome ticks at 30 BPM, alternating its two end-stop sounds and cutting the scene every three quarter notes. Two bass drum hits fall between each pair of ticks. A loose floor speaker flexes on each hit, with a rubber cord running from its basket to a nearby jack plate. The TV leaves a breath after each cut and answers with three short sine taps. The middle tap is softer and slightly late. The last tap changes pitch across the four replies, and the two-color wave pulses with each strike.

Run `npm run dev` in the VS Code terminal and open the address Vite prints. **M** toggles sound, **P** pauses the beat and **H** opens the studio drawer. In the Audio tab, Voice A controls the TV synth and Voice B controls the bass drum. The tempo control sets the metronome speed. The music runs at three times that tempo. Reset starts muted at 30 BPM on the metronome.

## Blender

Open [18-pendulum.blend](blender/18-pendulum.blend). The ten numbered scenes share the same stage mesh and instrument collection. The metronome measures 21 cm. Furniture uses the catalog dimensions. Each numbered scene has three named cameras. Step through frames 1–3 in camera view to preview them. Every camera tracks its own editable focus point and has its own lens. The wide parlor, arcade and Citrus views export the extent of their furniture so the whole arrangement fits on narrow screens. Every shot protects the framing of the metronome and television. The Exchange also frames the stepladder, and the arcade frames the pinball machine.

Move or rotate the **Floating television** parent in a shot to aim its light. The picture and its two rectangular emitters follow the housing. Each emitter mixes the two screen colors according to the area each color covers on its half of the glass.

To export edits from the saved Blender file, run the following from the sketch directory with Blender 5.3.

```sh
blender -b blender/18-pendulum.blend --python-exit-code 1 --python blender/export.py
```

The export writes the instrument, stage, ten furniture groups, and camera and light data into `public/models/`. The Three.js player preloads these assets before starting the beat. To regenerate the Blender file from the original catalog downloads and modeled geometry, run `blender -b --factory-startup --python-exit-code 1 --python blender/build.py`. Model credits ship with the sketch. [Asset credits](public/models/CREDITS.md)

## Studio

The shell, Box3D world, orbit camera, palette workshop, Strudel voices and settings API come from `14-tension`. Its lighting, shadows, material controls, bloom, focus, FPS and PNG export come from the Shatter and Tangle studios. Box3D drives the kinematic reed. Strudel and the stage animation share a transport, so the speaker and TV follow their notes through cuts, pauses and muted playback.

Camera edits adjust the framing across all shots. If a saved orbit puts furniture in front of the metronome or moves its swing out of frame, that cut uses its authored camera position. Save stores the settings and current beat position in `public/settings.json` during development. Reload restores the view and beat phase. Reset returns to the opening composition. Static builds save to the device.

Run `npm run check` for tests and a production build.
