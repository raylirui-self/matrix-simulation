/**
 * Era detection — mirrored from backend gui/backend/api/routes/media.py:_detect_era.
 * Shared across EraBanner, EraSplash, and AmbientLandscape so transitions are consistent.
 */
import { derived } from 'svelte/store';
import { stats, breakthroughs } from '$lib/stores/simulation';

export type Era = {
	name: string;
	/** Backend slug used by /media/landscape/image — must match sanitize logic. */
	slug: string;
	color: string;
	desc: string;
	check: (s: any, techs: string[]) => boolean;
};

export const ERAS: Era[] = [
	{
		name: 'Industrial Age',
		slug: 'industrial_age',
		color: '#ffd700',
		desc: 'Machines reshape the world',
		check: (_s, techs) => techs.includes('industrialization'),
	},
	{
		name: 'Trade Era',
		slug: 'trade_era',
		color: '#00ccff',
		desc: 'Commerce connects communities',
		check: (_s, techs) => techs.includes('trade_networks'),
	},
	{
		name: 'Bronze Age',
		slug: 'bronze_age',
		color: '#cd7f32',
		desc: 'Metal tools forge a new world',
		check: (_s, techs) => techs.includes('mining'),
	},
	{
		name: 'Agricultural Age',
		slug: 'agricultural_age',
		color: '#4a7a3a',
		desc: 'Settled life begins',
		check: (_s, techs) => techs.includes('agriculture'),
	},
	{
		name: 'Age of Awakening',
		slug: 'age_of_awakening',
		color: '#aa66ff',
		desc: 'Knowledge grows rapidly',
		check: (s) => s.avg_intelligence > 0.3,
	},
	{
		name: 'Tribal Expansion',
		slug: 'tribal_expansion',
		color: '#ff8844',
		desc: 'Clans spread across the land',
		check: (s) => s.alive_count > 80,
	},
	{
		name: 'Dawn of Tribes',
		slug: 'dawn_of_tribes',
		color: '#00ff88',
		desc: 'Small groups form bonds',
		check: (s) => s.alive_count > 20,
	},
	{
		name: 'Genesis',
		slug: 'genesis',
		color: '#5a8a5a',
		desc: 'Life stirs in the void',
		check: (s) => s.alive_count > 0,
	},
	{
		name: 'The Void',
		slug: 'the_void',
		color: '#ff4466',
		desc: 'Nothing remains...',
		check: () => true,
	},
];

export const currentEra = derived([stats, breakthroughs], ([$stats, $techs]) => {
	for (const era of ERAS) {
		if (era.check($stats, $techs)) return era;
	}
	return ERAS[ERAS.length - 1];
});
