#!/usr/bin/env python3

import argparse
import os
import shutil
import sys
import time
from io import BytesIO
from zipfile import ZipFile
import bs4
import gevent
import gevent.monkey
import httplib2
import logging
from gevent import GreenletExit
from gevent.lock import Semaphore
from urllib.parse import urljoin
gevent.monkey.patch_all()


logger = logging.getLogger('crawler')

zip_downloads_sem = Semaphore(5)
politeness = 1.5

SRC_EXTS = {'java': '.java', 'go': '.go', 'python': '.py'}
BLACKLIST = {'python': ['/ansible/ansible', '/bitcoinbook/bitcoinbook', '/nltk/nltk']}


def parse_search_pg(soup_url, soup):
    results_soup = soup.find("ul", {'class': 'repo-list'})
    repo_links = [x.a['href'] for x in results_soup('h3')]
    pagination = soup.find('div', {'class': 'pagination'})
    nxt_href = pagination.find(attrs={'class': 'next_page'})['href']

    # abs_repo_links = [urljoin(soup_url, x) for x in repo_links]
    return repo_links, urljoin(soup_url, nxt_href)


def get_zip_from_repo_url(url, retries=3):
    url = urljoin("https://github.com/", url)
    while 1:
        h = httplib2.Http()
        resp, content = h.request(url, headers={'cache-control': 'no-cache'})
        if resp.status != 200:
            if retries == 0:
                resp.raise_for_status()
            retries -= 1
            logger.warning("Non-200 resp. from results; waiting 10 seconds")
            time.sleep(10.0)
        else:
            break

    try:
        soup = bs4.BeautifulSoup(content, "html5lib")
        btn = soup.find(attrs={'class': 'get-repo-btn'})
        assert btn is not None
        part = btn['href']
        assert part is not None
    except:
        logger.error("Contents of unparseable page: %s\n%s" % (url, content))
        raise
    return urljoin(url, part)


def sanitize(s):
    if s[0] in ('_', '.'):
        s = '-' + s[1:]
    s = s.encode('ascii', 'replace').decode('ascii')
    return s


def crawl_if_new(repo_url, src_ext, retries=4):
    dest_dir_path = repo_url.strip('/').replace('/', '_')
    lock_dir_path = "_" + dest_dir_path

    # get a _ dir
    with zip_downloads_sem:
        try:
            os.mkdir(lock_dir_path)
        except OSError:
            logger.info("Couldn't mkdir %s; skipping" % (lock_dir_path,))
            return

        try:
            # check if exists
            if os.path.exists(dest_dir_path):
                logger.info("%s exists; skipping" % (dest_dir_path,))
                os.rmdir(lock_dir_path)
                return

            # get the .zip URL (for default branch; not necessarily 'master')
            zip_url = get_zip_from_repo_url(repo_url)
            
            # crawl
            content = download_zip_contents(zip_url, retries, dest_dir_path, lock_dir_path)

            # success, now unzip
            extract_zip(content, src_ext, lock_dir_path)

            # move _dir to dir
            logger.debug("moving %s to %s" % (lock_dir_path, dest_dir_path))
            os.rename(lock_dir_path, dest_dir_path)
        except Exception as e:
            # delete _ dir
            shutil.rmtree(lock_dir_path)
            logger.exception(e)


def extract_zip(content, src_ext, lock_dir_path):
    pre_root_files = 0
    with ZipFile(BytesIO(content), 'r') as z:
        for name in z.namelist():
            if '..' in name:
                pre_root_files += 1
            elif name.lower().endswith(src_ext):
                z.extract(name, sanitize(lock_dir_path))
            else:
                logger.debug('skipping %s' % (name,))
    if pre_root_files:
        logger.info("skipped %d unsafe zipped names" % (pre_root_files,))


def download_zip_contents(zip_url, retries, dest_dir_path, lock_dir_path):
    while 1:
        h = httplib2.Http()
        try:
            resp, content = h.request(zip_url,
                headers={'cache-control': 'no-cache'})
            time.sleep(politeness)
            if resp.status != 200:
                raise Exception("%d response" % resp.status)
            return content
        except (GreenletExit, KeyboardInterrupt):
            raise
        except Exception as e:
            if retries:
                logger.info("%s: %s; waiting 5sec" % (dest_dir_path, str(e)))
                time.sleep(5.0)
                retries -= 1
                continue
            else:
                logger.error("%s: %s" % (dest_dir_path, str(e)))
                logger.error("  was trying %s" % (zip_url,))
                logger.error("  ... but now giving up")
                os.rmdir(lock_dir_path)
                raise


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--language", "-l", default='java')
    args = arg_parser.parse_args()

    src_ext = SRC_EXTS[args.language]

    # then get to business
    h = httplib2.Http()
    repo_search_url = "https://github.com/search?langOverride=&q=language%3A"
    repo_search_url += args.language
    repo_search_url += "&repo=&start_value=1&type=Repositories"
    while 1:
        resp, content = h.request(repo_search_url,
                                  headers={'cache-control': 'no-cache'})
        if resp.status != 200:
            logger.info("Non-200 resp. from results; waiting 10 seconds")
            time.sleep(10.0)
            continue
        soup = bs4.BeautifulSoup(content, "html5lib")
        repos, repo_search_url = parse_search_pg(repo_search_url, soup)
        repos = [r for r in repos if r not in BLACKLIST.get(args.language, [])]
        jobs = [gevent.spawn(crawl_if_new, repo, src_ext) for repo in repos]
        try:
            gevent.joinall(jobs, timeout=900, raise_error=True)  # 15m
        except KeyboardInterrupt as e:
            gevent.killall(jobs, block=True, timeout=5)
            sys.exit(0)
        else:
            logger.info("Completed")
