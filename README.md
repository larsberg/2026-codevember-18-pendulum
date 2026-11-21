# 18 / Pendulum

A white mechanical metronome stands at the center of a petrol-blue cyclorama. Each Strudel click lands at the end of a swing and cuts the furniture, lights and camera together. A 55-inch television floats in a different position in each of the ten compositions. Cyan and blue light spill onto a mustard sofa. An amber picture lights a clockwork orrery set between two breakfast plates. The screen turns across a loaded bookcase, then hovers low beside a record player. An overhead cut looks down on an open aluminum stepladder leading from the floor up to the front of the lacquered counter. A striped runner lies to the left of the floor jack, clear of the cable and the steps. The next three shots look back through the conservatory, skim the floor beside the washers, and look over the pinball playfield and its painted backglass. The last two cuts move from Citrus, a lemon-yellow soda fountain in broad daylight, to Nocturne, a dark projection booth with a single cinema seat. The tenth click returns to the parlor from a second angle. A third pass uses the remaining cameras, and the opening view returns on click 30.

Click the sketch to hear **Composition C**, a 64-bar arrangement at 84 BPM (about 3:03 per loop). The metronome alternates its two end-stop sounds on beat one and cuts the camera every bar. One solo click opens the loop. The floor speaker joins on the second click and the TV snare answers on beat four of that bar. From bar three the snare plays two and four. Bars 9–24 give Composition B’s four-bar groove room to repeat. In bars 25–32 the kick moves its reply to the swung “and” of three and leaves the end of each phrase open. The drums gradually drop away until just an occasional snare answers the pendulum. The kick reenters in bar 47, and the full groove returns in bar 57. Bar 64 ends with a kick on one and a snare on two, leaving space for the opening clicks to come around again. The cone follows each kick, and the two-color TV picture follows the snare’s audio.

Run `npm run dev` in the VS Code terminal and open the address Vite prints. **M** toggles sound, **P** pauses the beat and **H** opens the studio drawer. In the Audio tab, open **TV wave snare** and tap beats 1–4 to choose which quarter notes the snare may play. The arrangement brings those strokes in and out. Adjust its level, tuning, tone and decay by ear. Wave height and density control the picture. Save settings keeps the pattern and sound for the next session. The tempo control sets the metronome speed. Each click spans four quarter notes. Reset starts muted at 21 BPM on the metronome (84 BPM for the drums).

## Blender

Open [18-pendulum.blend](blender/18-pendulum.blend). The ten numbered scenes share the same stage mesh and instrument collection. The metronome measures 21 cm. Furniture uses the catalog dimensions. Each numbered scene has three named cameras. Step through frames 1–3 in camera view to preview them. Every camera tracks its own editable focus point and has its own lens. The wide parlor, arcade and Citrus views export the extent of their furniture so the whole arrangement fits on narrow screens. Every shot protects the framing of the metronome and television. The Exchange also frames the stepladder, and the arcade frames the pinball machine.

Move or rotate the **Floating television** parent in a shot to aim its light. The picture and its two rectangular emitters follow the housing. Each emitter mixes the two screen colors according to the area each color covers on its half of the glass.

To export edits from the saved Blender file, run the following from the sketch directory with Blender 5.3.

```sh
blender -b blender/18-pendulum.blend --python-exit-code 1 --python blender/export.py
```

The export writes the instrument, stage, ten furniture groups, and camera and light data into `public/models/`. The Three.js player preloads these assets before starting the beat. To regenerate the Blender file from the original catalog downloads and modeled geometry, run `blender -b --factory-startup --python-exit-code 1 --python blender/build.py`. Model credits ship with the sketch. [Asset credits](public/models/CREDITS.md)

## Studio

The shell, Box3D world, orbit camera, palette workshop, Strudel voices and settings API come from `14-tension`. Its lighting, shadows, material controls, bloom, focus, FPS and PNG export come from the Shatter and Tangle studios. Box3D drives the kinematic reed. Strudel and the floor speaker share a transport. The TV reads its own audio channel and returns to a flat line when paused or muted.

Drag to orbit or pan, and scroll to zoom. The view holds after release until the next metronome cut, when the incoming shot takes its own framing. The Camera tab and Save let you apply a framing adjustment across shots. If that adjustment hides the metronome on a cut, the incoming shot uses its authored camera position. Save stores the settings and current beat position in `public/settings.json` during development. Reload restores the view and beat phase. Reset returns to the opening composition. Static builds save to the device.

Run `npm run check` for tests and a production build.
