import {websiteCardFacts} from './current_website_cards_v142.mjs';

// The older Extreme Footwork wrapper owns its complete repetition schedule
// and bypasses the new 756 boundary. Refuse the unintegrated combination
// before any opening effects or card actions; do not silently skip 755/756.
export function guardWebsiteCardSchedules(root, game, swogi, metadata, order) {
  const effects = new Set(websiteCardFacts(root).cards
    .filter(c => c.kind === 'cloud_silence' || c.kind === 'cloud_steps')
    .map(c => c.runtime_id));
  const indices = new Map(game.players.map((p, i) => [p, order[i]]));
  function check(p, executing) {
    const counters = metadata()?.pending.find(s => s.player_index === indices.get(p));
    if ((effects.has(executing) || p.cards.some(id => effects.has(id)) ||
         counters?.buff755 > 0 || counters?.buff756 > 0) &&
        p.cards.some(id => swogi[id]?.name === 'Current Extreme Footwork')) {
      throw new Error('website_cards_v142r2:755_756_extreme_footwork_schedule_unintegrated');
    }
  }
  for (const p of game.players) check(p);
  const play = game.play_card.bind(game);
  game.play_card = function(id, slot) {
    check(this.players[0], id);
    return play(id, slot);
  };
  const body = game.executeWebsiteCard142.bind(game);
  game.executeWebsiteCard142 = function(id) {
    check(this.players[0], id);
    return body(id);
  };
}
