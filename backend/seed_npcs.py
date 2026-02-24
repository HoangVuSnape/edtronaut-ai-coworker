import asyncio, asyncpg, json
from datetime import datetime, timezone

async def seed():
    try:
        conn = await asyncpg.connect('postgresql://edtronaut:edtronaut_secret@postgres:5432/edtronaut')
        await conn.execute('DELETE FROM npcs;')
        now = datetime.now(timezone.utc)
        npcs = [
            ('gucci_ceo', 'Marco Bizzarri', 'Chief Executive Officer, Gucci', '', {}),
            ('gucci_chro', 'Elena Rossi', 'Chief Human Resources Officer, Gucci', '', {}),
            ('gucci_eb_ic', 'Alessandro Vitale', 'Investment Banker, Gucci Group Finance', '', {}),
        ]
        for nid, name, role, prompt, traits in npcs:
            await conn.execute(
                'INSERT INTO npcs (id, name, role_title, system_prompt_template, traits, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7)',
                nid, name, role, prompt, json.dumps(traits), now, now
            )
            print(f'Seeded NPC: {nid}')
        await conn.close()
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(seed())
