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
  ["large_straight:courtroom", "yahtzee:documentary"]
);
const yahtzeeStep = timeline.steps.find((step) => step.box === "yahtzee");
assert.strictEqual(yahtzeeStep.cutaway.cue, "documentary");
assert.ok(yahtzeeStep.cutaway.line.includes("rolled a Yahtzee"));
assert.ok(yahtzeeStep.cutaway.line.includes("Anchor Bar"));
assert.strictEqual(timeline.finale.cutaway, null);
const straight = timeline.scenes.find((scene) => scene.cue === "courtroom" && scene.box === "large_straight");
assert.strictEqual(straight.drama, 40);
assert.strictEqual(straight.who, "Erin");
const sports128 = timeline.scenes.find((scene) => scene.cue === "sports");
assert.ok(sports128.line.includes("Erin has not"));
assert.ok(sports128.line.includes("74"));

function scenesFor(seq) {
  return replay.buildTimeline(payload.games.find((row) => row.game_seq === seq));
}

const hook = scenesFor(112);
assert.strictEqual(hook.scenes[0].line, "Rarely seen in the wild, the Erin has rolled a Yahtzee at The Butcher's Hook.");

const atlas = scenesFor(122);
const regulars = atlas.scenes.find((scene) => scene.cue === "regulars");
assert.strictEqual(regulars.deficit, 42);
assert.strictEqual(regulars.line, "Back from 42 down, Jordan? I've seen pints with less fizz.");
assert.deepStrictEqual(
  atlas.cutaways.map((row) => row.box + ":" + row.cue),
  ["yahtzee:documentary", "chance:regulars"]
);
assert.strictEqual(atlas.cutaways[1].about, "yahtzee");

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
  built.scenes.forEach((scene) => {
    assert.strictEqual(/\b(erin|jordan)\b/.test(scene.line), false, scene.line);
    assert.strictEqual(/five of a kind/i.test(scene.line), false, scene.line);
    if (row.venue && scene.cue !== "regulars") assert.ok(scene.line.includes(row.venue), scene.line);
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
