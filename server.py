import datetime
import sys
import asyncio
import os
import logging
import argparse
from functools import partial

from aiohttp import web
import aiofiles


def arg_parser():
    parser = argparse.ArgumentParser(description='Python send-zip utility')
    
    parser.add_argument('-d', '--debug',
                        action='store_true',  default=None, help='If provided enable debug logging')
    parser.add_argument('-t', '--throttling',  default=None, type=int, help='Provide how many tics will be beetwen chunk sents')
    parser.add_argument('-p', '--path', default='./test_photos', help='Path to folder with photos. This path directory may include hash directories with photos')

    args = parser.parse_args()

    return args


async def archive(request, throttling, root_photos_path, chunk_size=4096):
    response = web.StreamResponse()

    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'

    archive_hash = request.match_info['archive_hash']
    photos_path = os.path.join(root_photos_path, archive_hash)
    
    if not os.path.exists(photos_path):
        raise web.HTTPNotFound(text="Извините, данный архив не найден или был удалён.")
    
    await response.prepare(request)

    process = await asyncio.create_subprocess_exec(
        'zip', '-r', '-', '.',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=photos_path)

    try:
        while True:
            stdout_chunk = await process.stdout.read(chunk_size)
            if not stdout_chunk:
                break
    
            logging.debug('Sending archive chunk..')
            
            await response.write(stdout_chunk)
            if throttling:
                await asyncio.sleep(throttling)
    except asyncio.CancelledError:
        logging.debug('Download was interrupted')
        raise
    finally:
        if process.returncode is None:
            process.kill()
            await process.communicate()

        response.force_close()
                                     
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    args = arg_parser()
    
    logging.basicConfig(format="%(levelname)-8s [%(asctime)s] %(message)s", level=logging.DEBUG if args.debug else logging.INFO)
    
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', partial(archive, throttling=args.throttling, root_photos_path=args.path)),
    ])
    web.run_app(app)
