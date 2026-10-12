/* Timeline for the scorecard replay. Run with node. */
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const replay = require("../dashboard/scorecards/replay.js");

const gamesJs = fs.readFileSync(
  path.join(__dirname, "../dashboard/scorecards/games.js"),
  "utf8"
);
const payload = JSON.parse(gamesJs.slice(gamesJs.indexOf("=") + 1).trim().replace(/;$/, ""));
const game = payload.games.find((row) => row.game_seq === 128);

const timeline = replay.buildTimeline(game);
assert.strictEqual(timeline.steps.length, 15);
assert.deepStrictEqual(
  timeline.steps.map((step) => step.box),
  replay.ORDER.map((pair) => pair[0])
);
assert.strictEqual(timeline.steps[0].box, "ones");
assert.strictEqual(timeline.steps[12].box, "yahtzee");
assert.strictEqual(timeline.steps[13].box, "chance");
assert.strictEqual(timeline.steps[14].box, "yahtzee_bonus");

let erin = 0;
let jordan = 0;
timeline.steps.forEach((step) => {
  erin += step.points.erin;
  jordan += step.points.jordan;
  assert.strictEqual(step.running.erin, erin);
  assert.strictEqual(step.running.jordan, jordan);
  assert.strictEqual(step.margin, jordan - erin);
  assert.ok(step.t >= 0);
  assert.ok(step.holdMs > 0);
  assert.ok(!/erin|jordan/.test(step.caption));
  assert.ok(step.caption.includes("Erin") && step.caption.includes("Jordan"));
});
assert.strictEqual(timeline.finale.running.erin, erin);
assert.strictEqual(timeline.finale.running.jordan, jordan);
assert.strictEqual(timeline.finale.caption, game.story);
assert.ok(timeline.finale.scoreLine.startsWith("Jordan"));

const focusBoxes = timeline.steps.filter((step) => step.focus).map((step) => step.box);
assert.deepStrictEqual(focusBoxes, [
  "upper_bonus",
  "four_of_a_kind",
  "large_straight",
  "yahtzee",
]);
const yahtzee = timeline.steps.find((step) => step.box === "yahtzee");
assert.strictEqual(yahtzee.points.erin, 50);
assert.strictEqual(yahtzee.points.jordan, 0);
assert.strictEqual(yahtzee.holdMs, replay.FOCUS_MS);
assert.ok(yahtzee.caption.includes("Yahtzee"));

assert.ok(timeline.durationMs >= 10000 && timeline.durationMs <= 20000);
assert.strictEqual(
  timeline.durationMs,
  timeline.steps.reduce((sum, step) => sum + step.holdMs, 0)
);
assert.strictEqual(game.venue, "Anchor Bar");
assert.ok(timeline.cutaways.length <= 2);
assert.deepStrictEqual(
  timeline.cutaways.map((row) => row.box + ":" + row.cue),
  ["yahtzee:documentary", "chance:courtroom"]
);
assert.strictEqual(
  timeline.steps.find((step) => step.cutaway && step.cutaway.cue === "courtroom").cutaway.line,
  "Jordan, you are charged with scoring 0 on Yahtzee at Anchor Bar."
);
const yahtzeeStep = timeline.steps.find((step) => step.box === "yahtzee");
assert.strictEqual(yahtzeeStep.cutaway.cue, "documentary");
assert.ok(yahtzeeStep.cutaway.line.includes("rolled a Yahtzee"));
assert.ok(yahtzeeStep.cutaway.line.includes("Anchor Bar"));
assert.strictEqual(timeline.finale.cutaway, null);
const straight = timeline.scenes.find((scene) => scene.cue === "courtroom" && scene.box === "large_straight");
assert.strictEqual(straight.drama, 40);
assert.strictEqual(straight.who, "Erin");
assert.strictEqual(
  straight.line,
  "Erin, you are charged with throwing away 40 points on large straight at Anchor Bar."
);
const fourKind = timeline.scenes.find((scene) => scene.cue === "courtroom" && scene.box === "four_of_a_kind");
assert.strictEqual(
  fourKind.line,
  "Erin, you are charged with scoring 0 on four of a kind at Anchor Bar."
);
assert.strictEqual(fourKind.line.includes("27"), false);
const sports128 = timeline.scenes.find((scene) => scene.cue === "sports");
assert.ok(sports128.line.includes("Erin has not"));
assert.ok(sports128.line.includes("74"));

function scenesFor(seq) {
  return replay.buildTimeline(payload.games.find((row) => row.game_seq === seq));
}

const hook = scenesFor(112);
assert.strictEqual(
  hook.scenes.find((scene) => scene.cue === "documentary").line,
  "Rarely seen in the wild, the Erin has rolled a Yahtzee at The Butcher's Hook."
);

const atlas = scenesFor(122);
const regulars = atlas.scenes.find((scene) => scene.cue === "regulars");
assert.strictEqual(regulars.deficit, 42);
assert.strictEqual(regulars.line, "Back from 42 down, Jordan? I've seen pints with less fizz.");
assert.deepStrictEqual(
  atlas.cutaways.map((row) => row.box + ":" + row.cue),
  ["yahtzee:documentary", "chance:courtroom"]
);
assert.strictEqual(
  atlas.steps.find((step) => step.cutaway && step.cutaway.cue === "courtroom").cutaway.line,
  "Erin, you are charged with scoring 0 on Yahtzee at The Atlas."
);
const atlasPlan = replay.planPlayback(atlas.steps);
const atlasScenes = atlasPlan.filter((action) => action.kind === "scene" || action.kind === "scene-after");
assert.strictEqual(atlasScenes.length, 2);
assert.strictEqual(atlasScenes[1].kind, "scene-after");

function boardBetween(plan) {
  const first = plan.findIndex((action) => action.kind === "scene" || action.kind === "scene-after");
  const second = plan.findIndex((action, index) => index > first && (action.kind === "scene" || action.kind === "scene-after"));
  return plan.slice(first + 1, second).reduce((sum, action) => {
    return sum + (action.kind === "board" || action.kind === "bridge" ? action.wait : 0);
  }, 0);
}
const spaced = [];
for (let i = 0; i < 8; i += 1) spaced.push({ holdMs: 700, cutaway: null });
spaced[1].cutaway = { cue: "documentary" };
spaced[2].cutaway = { cue: "regulars" };
const spacedPlan = replay.planPlayback(spaced);
const spacedScenes = spacedPlan.filter((action) => action.kind === "scene" || action.kind === "scene-after");
assert.strictEqual(spacedScenes[1].kind, "scene");
assert.ok(boardBetween(spacedPlan) >= replay.BOARD_GAP_MS);

const bothBonus = scenesFor(124);
assert.ok(!bothBonus.scenes.some((scene) => scene.cue === "sports"));

const anchor = scenesFor(129);
const desk = anchor.scenes.find((scene) => scene.cue === "sports");
assert.strictEqual(desk.upper, 66);
assert.strictEqual(desk.otherUpper, 60);
assert.strictEqual(
  desk.line,
  "Sources confirm Jordan has reached 66 in the upper section at Anchor Bar. Erin has not. More at 11."
);

const again = replay.buildTimeline(game);
assert.deepStrictEqual(again.cutaways, timeline.cutaways);

payload.games.forEach((row) => {
  const built = replay.buildTimeline(row);
  assert.ok(built.cutaways.length <= 2);
  built.steps.concat([built.finale]).forEach((step) => {
    assert.strictEqual(/throwing away|threw away/.test(step.caption), false, step.caption);
  });
  built.scenes.forEach((scene) => {
    assert.strictEqual(/\b(erin|jordan)\b/.test(scene.line), false, scene.line);
    assert.strictEqual(/five of a kind/i.test(scene.line), false, scene.line);
    if (row.venue && scene.cue !== "regulars") assert.ok(scene.line.includes(row.venue), scene.line);
    if (scene.cue !== "courtroom") return;
    if (scene.box === "full_house" || scene.box === "small_straight" || scene.box === "large_straight") {
      const fixed = { full_house: ["25", "full house"], small_straight: ["30", "small straight"], large_straight: ["40", "large straight"] };
      assert.ok(scene.line.includes("throwing away " + fixed[scene.box][0] + " points on " + fixed[scene.box][1]), scene.line);
      return;
    }
    assert.match(scene.line, /scoring 0 on /);
    assert.strictEqual(scene.line.includes("throwing away"), false, scene.line);
    assert.strictEqual(/\d/.test(scene.line.replace("scoring 0", "")), false, scene.line);
  });
});

const comeback = replay.buildTimeline({
  erin: { scores: { sixes: 30 } },
  jordan: { scores: { three_of_a_kind: 40 } },
  focus: [],
  story: "",
});
assert.deepStrictEqual(
  comeback.cutaways.map((row) => row.box + ":" + row.cue),
  ["three_of_a_kind:courtroom", "four_of_a_kind:regulars"]
);
assert.strictEqual(
  comeback.scenes.find((scene) => scene.box === "sixes").line,
  "Jordan, you are charged with scoring 0 on sixes."
);
assert.strictEqual(
  comeback.scenes.find((scene) => scene.box === "three_of_a_kind").line,
  "Erin, you are charged with scoring 0 on three of a kind."
);

const fixedHouse = replay.buildTimeline({
  erin: { scores: { full_house: 25 } },
  jordan: { scores: { full_house: 0 } },
  venue: "Anchor Bar",
  focus: [],
  story: "",
});
assert.strictEqual(
  fixedHouse.scenes.find((scene) => scene.cue === "courtroom").line,
  "Jordan, you are charged with throwing away 25 points on full house at Anchor Bar."
);

const variableKind = replay.buildTimeline({
  erin: { scores: { four_of_a_kind: 0 } },
  jordan: { scores: { four_of_a_kind: 22 } },
  venue: "The Atlas",
  focus: [],
  story: "",
});
const variableLine = variableKind.scenes.find((scene) => scene.cue === "courtroom").line;
assert.strictEqual(variableLine, "Erin, you are charged with scoring 0 on four of a kind at The Atlas.");
assert.strictEqual(variableLine.includes("22"), false);

const smallScratch = replay.buildTimeline({
  erin: { scores: { ones: 0 } },
  jordan: { scores: { ones: 3 } },
  focus: [],
  story: "",
});
assert.strictEqual(
  smallScratch.scenes.find((scene) => scene.cue === "courtroom").line,
  "Erin, you are charged with scoring 0 on aces."
);
const nothing = replay.buildTimeline({
  erin: { scores: { chance: 0 } },
  jordan: { scores: { chance: 0 } },
  focus: [],
  story: "",
});
assert.strictEqual(nothing.scenes.some((scene) => scene.cue === "courtroom"), false);

const quiet = replay.buildTimeline({
  erin: { scores: { chance: 10 } },
  jordan: { scores: { chance: 10 } },
  focus: [],
  story: "They finished level, box for box.",
});
assert.strictEqual(quiet.steps.filter((step) => step.focus).length, 0);
assert.ok(quiet.durationMs >= 10000 && quiet.durationMs <= 20000);
assert.strictEqual(replay.scoreLine(10, 10), "Level at 10.");
assert.strictEqual(replay.leadLine(0), "Level.");
assert.strictEqual(replay.leadLine(12), "Jordan ahead by 12.");
assert.strictEqual(replay.leadLine(-4), "Erin ahead by 4.");

const forbidden = /\b(chase|pipeline|seed|merchant|scratch|3oak|4oak|bank)\b/i;
timeline.steps.concat([timeline.finale]).forEach((step) => {
  assert.strictEqual(forbidden.test(step.caption), false, step.caption);
  if (step.scoreLine) assert.strictEqual(forbidden.test(step.scoreLine), false);
});

console.log("test_replay_timeline: ok");
