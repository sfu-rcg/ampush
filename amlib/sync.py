import re
from amlib import conf, log, ad_op, utils, cnx
from amlib import file_map as fm
from amlib import ad_map as adm
import ldap.modlist as modlist


'''
Functions for comparing and merging the diffs between
flat file automount maps (authoritative) and automount
maps in Active Directory.

Part of ampush. https://github.com/sfu-rcg/ampush
Copyright (C) 2016-2017 Research Computing Group, Simon Fraser University.
'''


def preflight():
    ad_op.verify_am_container_exists()
    utils.verify_ff_am_dir_exists()
    utils.verify_ff_master_exists()
    fm.detect_orphans()
    return


def do(maps=None, dry_run=True):
    ''' Let's DO THIS THING '''
    preflight()

    # argparse shoves "None" in the list which is not super helpful
    maps = filter(None, maps)

    if len(maps) == 0:
        log.m.debug('Default --sync action: sync all maps')
        all_parent_maps(dry_run=dry_run)
        all_map_contents(dry_run=dry_run)
    else:  # >=1 maps passed to --sync
        log_msg = 'Syncing maps passed as args: ' + ' '.join(maps)
        log.m.debug(log_msg)
        for map_name in maps:
            parent_map(map_name=map_name, dry_run=dry_run)
            conflicts_found = None
            conflicts_found = map_contents(map_name=map_name,
                                           dry_run=dry_run)
            if conflicts_found is True:
                log.m.info('Resyncing ' + map_name)
                map_contents(map_name=map_name, dry_run=dry_run)
    return


def all_parent_maps(dry_run=True):
    '''
    Sync just the parent map objects themselves. Do NOT touch their
contents yet. Create new maps where necessary. Recursively delete maps
in AD that have no flat file equivalent.
    '''
    # Map exists in flatfile but not AD? create it in AD
    # Map exists in AD but not in flatfile? delete it from AD
    for ff_map_name in fm.get_names():
        parent_map(map_name=ff_map_name, dry_run=dry_run)
    clean_ad(dry_run=dry_run)
    return


def all_map_contents(dry_run=True):
    for ff_map_name in fm.get_names():
        conflicts_found = None
        conflicts_found = map_contents(map_name=ff_map_name, dry_run=dry_run)
        if conflicts_found is True:
            log.m.info('Resyncing ' + ff_map_name)
            map_contents(map_name=ff_map_name, dry_run=dry_run)
    return


def clean_ad(dry_run=True):
    ''' Map exists in AD but not on the filesystem? Delete it from AD. '''
    for ad_map_name in adm.get_names():
        if ad_map_name not in fm.get_names():
            ad_map_cn = utils.map_cn(ad_map_name)
            log_msg = ad_map_name + ' exists in AD but not on filesystem'
            log.m.info(log_msg)
            ad_op.delete(cn=ad_map_cn, recurse=True, dry_run=dry_run)
    return


def parent_map(map_name=None, dry_run=True):
    ''' Create a nisMap object in AD. Home to one or more nisObjects.
 https://www.ietf.org/rfc/rfc2307.txt '''
    # log.m.debug('sync.parent_map:' + map_name)

    ad_map_cn = utils.map_cn(map_name)
    if ad_op.get(ad_map_cn) is not None:
        # log.m.debug('Parent map already exists: ' + map_name)
        return

    log_msg = 'Flat file map {0} has no AD equivalent'.format(map_name)
    log.m.debug(log_msg)

    log_msg = 'Creating AD:' + map_name
    log_msg = utils.dry_msg(log_msg, dry_run=dry_run)

    # for master map keys, nisMapName SHOULD have a leading slash
    attrs = {}
    attrs['objectClass'] = ['top', conf.c['t_nismap']]
    attrs['cn'] = [map_name]
    attrs['name'] = [map_name]
    attrs['nisMapName'] = [map_name]

    ml = modlist.addModlist(attrs)
    ad_op.add_obj(dn=utils.map_cn(map_name),
                  debug_attrs=attrs,
                  attrs=ml,
                  dry_run=dry_run)
    return


def map_contents(map_name=None, dry_run=True):
    '''
Read a single flat file map from disk.

Pass 1: Keys that exist in AD but not in flat file maps: delete from AD.
Pass 2: Keys that exist in flat file maps but not in AD: create in AD.
Pass 3: Keys that exist in both places but whose values differ:
        delete from AD, create in AD with updated info.
    '''
    # log.m.debug('sync.map_contents:'+map_name)

    conflicts_found = None
    if ad_op.conflict_catcher(map_name=map_name) is True:
        conflicts_found = True

    ff_map = fm.parse(map_name)
    ad_map = adm.parse(map_name)

    # Pass 1
    if ad_map is not None:
        for k in ad_map.keys():
            if k not in ff_map:
                target = 'cn={0},cn={1},{2}'
                target = target.format(k, map_name, conf.c['am_container'])
                ad_op.delete(cn=target, dry_run=dry_run)

    # Pass 2
    for k in ff_map.keys():
        if ad_map is not None:
            if k not in ad_map:
                ad_op.create_map_entry(map_name=map_name,
                                       entry_k=k,
                                       entry_v=ff_map[k],
                                       dry_run=dry_run)
        else:
            pass
            # log_msg = 'Null result from AD for {0}:{1}'.format(map_name, k)
            # log.m.debug(log_msg)

    # refresh our view of AD before proceeding
    ad_map = adm.parse(map_name)

    # Pass 3
    for k in ff_map.keys():
        if ad_map is None:
            log_msg = "Skipping sync pass 3; AD:{0}=>{1} does not exist " + \
                      "yet. You're probably in dry run mode. If you " + \
                      "aren't, file a bug! I'm really sorry."
            log_msg = log_msg.format(map_name, k)
            log.m.info(log_msg)
            continue
        if k in ad_map:
            in_sync = True

            # common maps: iterate over server_dir, server_hostname & options
            # master map: iterate over map, options
            for attr, x in ff_map[k].items():
                if ad_map[k][attr] != ff_map[k][attr]:
                    in_sync = False

            if in_sync is False:
                target = 'cn={0},cn={1},{2}'
                log_msg = 'AD:{1} - {0} is out of sync'.format(k, map_name)
                log.m.info(log_msg)

                log_msg = 'ad_current: ' + str(ad_map[k])
                log.m.debug(log_msg)

                target = target.format(utils.strip_slash(k),
                                       map_name,
                                       conf.c['am_container'])
                ad_op.delete(cn=target, dry_run=dry_run)

                ad_op.create_map_entry(map_name=map_name,
                                       entry_k=k,
                                       entry_v=ff_map[k],
                                       dry_run=dry_run)
    # one more time...
    if ad_op.conflict_catcher(map_name=map_name) is True:
        conflicts_found = True
    return conflicts_found  # True == we should re-run the sync
