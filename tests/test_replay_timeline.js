/* Timeline for the scorecard replay. Run with node. */
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const cutaways = require("../dashboard/scorecards/cutaways.js");
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

const cues = Object.fromEntries(timeline.cutaways.map((row) => [row.box, row.cue]));
assert.strictEqual(cues.yahtzee, "yahtzee");
assert.strictEqual(cues.upper_bonus, "bonus");
assert.strictEqual(cues.large_straight, "scratch");
timeline.cutaways.forEach((row) => {
  assert.ok(["yahtzee", "bonus", "scratch", "comeback"].includes(row.cue));
  assert.ok(row.gag);
});
const yahtzeeStep = timeline.steps.find((step) => step.box === "yahtzee");
assert.strictEqual(yahtzeeStep.cutaway.cue, "yahtzee");
assert.ok(yahtzeeStep.cutaway.gag);
assert.ok(yahtzeeStep.cutaway.ms >= 2000 && yahtzeeStep.cutaway.ms <= 4000);
assert.ok(yahtzeeStep.cutaway.title.startsWith("Erin"));
assert.ok(yahtzeeStep.cutaway.line.startsWith("This is like the time"));
assert.strictEqual(timeline.finale.cutaway, null);

const again = replay.buildTimeline(game);
assert.deepStrictEqual(
  timeline.steps.map((step) => (step.cutaway ? step.cutaway.gag : null)),
  again.steps.map((step) => (step.cutaway ? step.cutaway.gag : null))
);

const catalog = cutaways.listGags();
assert.ok(catalog.length >= 16);
["yahtzee", "bonus", "scratch", "comeback"].forEach((cue) => {
  assert.ok(catalog.filter((row) => row.cue === cue).length >= 4);
});
const forbidden = /\b(chase|pipeline|seed|merchant|scratch|3oak|4oak|bank)\b/i;
const borrowed = /\b(peter|griffin|quagmire|stewie|giggity|homer|bart|simpsons|family guy)\b/i;
catalog.forEach((row) => {
  assert.ok(row.ms >= 2000 && row.ms <= 4000);
  [row.title, row.line, row.lineAtVenue].forEach((text) => {
    assert.strictEqual(forbidden.test(text), false, text);
    assert.strictEqual(borrowed.test(text), false, text);
    assert.strictEqual(/\berin\b/.test(text), false, text);
    assert.strictEqual(/\bjordan\b/.test(text), false, text);
  });
  assert.ok(row.title.includes("Erin"));
});
const stable = { cue: "scratch" };
const stableAgain = { cue: "scratch" };
const ctx = {
  gameSeq: 128,
  index: 0,
  who: "Erin",
  other: "Jordan",
  venue: "Anchor Bar",
  label: "Large straight",
};
cutaways.decorate(stable, ctx);
cutaways.decorate(stableAgain, ctx);
assert.strictEqual(stable.gag, stableAgain.gag);
assert.ok(stable.line.includes("Erin"));
const listed = catalog.find((row) => row.cue === "scratch" && row.id === stable.gag);
if (listed.line !== listed.lineAtVenue) {
  assert.ok(stable.line.includes("Anchor Bar"));
}

const comeback = replay.buildTimeline({
  erin: { scores: { sixes: 30 } },
  jordan: { scores: { three_of_a_kind: 40 } },
  focus: [],
  story: "",
});
assert.deepStrictEqual(
  comeback.cutaways.map((row) => row.box + ":" + row.cue),
  ["three_of_a_kind:comeback"]
);
const comebackStep = comeback.steps.find((step) => step.box === "three_of_a_kind");
assert.strictEqual(comebackStep.cutaway.cue, "comeback");
assert.ok(comebackStep.cutaway.gag);
assert.ok(comebackStep.cutaway.title.includes("Jordan"));

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

timeline.steps.concat([timeline.finale]).forEach((step) => {
  assert.strictEqual(forbidden.test(step.caption), false, step.caption);
  if (step.scoreLine) assert.strictEqual(forbidden.test(step.scoreLine), false);
  if (step.cutaway && step.cutaway.line) {
    assert.strictEqual(forbidden.test(step.cutaway.line), false, step.cutaway.line);
    assert.strictEqual(forbidden.test(step.cutaway.title), false, step.cutaway.title);
    assert.strictEqual(/\berin\b/.test(step.cutaway.line), false);
    assert.strictEqual(/\bjordan\b/.test(step.cutaway.title), false);
  }
});

console.log("test_replay_timeline: ok");
