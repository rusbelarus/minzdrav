'''async def get_new_variant(vaadin, route, session):
    headers = {
            "Cookie": f"{route} {session}",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept-Encoding": "gzip, deflate"
        }
    payload = {"csrfToken": f"{vaadin}",
               "rpc": [["0", "com.vaadin.shared.ui.ui.UIServerRpc", "resize", [980, 2486, 2486, 980]],
                       ["59", "com.vaadin.shared.ui.button.ButtonServerRpc", "disableOnClick", []],
                       ["59", "com.vaadin.shared.ui.button.ButtonServerRpc", "click", [
                           {"altKey": False, "button": "LEFT", "clientX": 134, "clientY": 337, "ctrlKey": False,
                            "metaKey": False, "relativeX": 113, "relativeY": 10, "shiftKey": False, "type": 1}]]],
               "syncId": 0, "clientId": 0}
    result = requests.post(
        "https://iom-spo.edu.rosminzdrav.ru/UIDL/?v-uiId=0", headers=headers, data=json.dumps(payload),
        proxies=proxies).text
    data = re.findall(r"for\(;;\);\[(.*)]", result)[0]
    data = json.loads(data)
    syncId = data['syncId']
    clientId = data['clientId']
    variants_count = data['changes'][0][2][1]['rows']
    while variants_count < 500:
        payload = {"csrfToken": f"{vaadin}",
                   "rpc": [["0", "com.vaadin.shared.ui.ui.UIServerRpc", "resize", [980, 2486, 2486, 980]],
                           ["59", "com.vaadin.shared.ui.button.ButtonServerRpc", "disableOnClick", []],
                           ["59", "com.vaadin.shared.ui.button.ButtonServerRpc", "click", [
                               {"altKey": False, "button": "LEFT", "clientX": 134, "clientY": 337, "ctrlKey": False,
                                "metaKey": False, "relativeX": 113, "relativeY": 10, "shiftKey": False, "type": 1}]]],
                   "syncId": syncId, "clientId": clientId}
        result = requests.post(
            "https://iom-spo.edu.rosminzdrav.ru/UIDL/?v-uiId=0", headers=headers, data=json.dumps(payload),
            proxies=proxies).text
        data = re.findall(r"for\(;;\);\[(.*)]", result)[0]
        data = json.loads(data)
        syncId = data['syncId']
        clientId = data['clientId']
        variants_count = data['changes'][0][2][1]['rows']
        print(variants_count)

async def write(app):
    async with app['pool'].acquire() as conn:
        _ioms = await Iom.get_vo_ioms(conn)
    #to_write = dict()
    for _iom in _ioms:
        async with app['pool'].acquire() as conn:
            iom = await Iom.get_vo_iom(conn, _iom)
        if IomKind.TRAINING.value in iom.iomkind or IomKind.INTERACTIVE.value in iom.iomkind:
            continue
        with open('ioms_vo_clean.txt', 'a') as inf:
            inf.write(f'{iom.name} - {iom.enddate} - {iom.id}\n')
    print('done')
        #_spec = iom.additionalspecialities.split(',')
        #spec = [s.strip() for s in _spec]
        #spec.append(iom.specialityname.strip())
        #for _ in spec:
        #    if len(_) == 0:
        #        spec.remove(_)
        #to_write.update({iom.name: sorted(spec)})
    #for k, v in sorted(to_write.items()):
    #    with open('ioms_vo.txt', 'a') as inf:
    #        inf.write(
    #            f'{k} - {v}'
               # f'Тест с ответами по теме «{k}»\n\n'
               # f'Вашему вниманию представляется тест нмо с ответами для медицинских работников (медсестры и врачи) по теме «{k}».\n'
               # f'Данный тест нмо с ответами для медицинского персонала среднего и высшего звена (медицинские сестры и врачи) по теме «{k}» позволяет успешнее подготовиться к итоговой аттестации и/или понять данную тему.\n\n'
               # f'Специальности для предварительного и итогового тестирования:\n\n'
               # f'{", ".join(v)}.\n\n\n')'''

'''for key, value in STATE.items():
               if 'caption' in value.keys():
                   if VaadinActions.JUMP in value['caption']:
                       if 'caption' in value.keys():
                           if VaadinActions.NEW_VARIANT in value['caption']:
                               if 'styles' in value.keys():
                                   logger.info("STYLES")
                                   continue
                               else:
                                   session = await click_by_key(
                                       session, host=host, key=key, client_id=session.vaadin.client_id)
                                   print(session)

           for key, value in STATE.items():
               if 'caption' in value.keys():
                   if VaadinActions.JUMP in value['caption']:
                       session = await click_by_key(
                           session=session, host=host, key=key, client_id=session.vaadin.client_id)
                       print(session)
                       if session:
                           STATE = session.vsess.state
                           for k, v in STATE.items():
                               if 'caption' in v.keys():
                                   if VaadinActions.BEFORE in v['caption']:
                                       session = await click_by_key(
                                           session=session, host=host, key=k, client_id=session.vsess.client_id)
                                       print(session)
                                       if session:
                                           STATE = session.vsess.state
                                           break
                           for k, v in STATE.items():
                               if 'caption' in v.keys():
                                   if VaadinActions.NEW_VARIANT in v['caption']:
                                       if 'styles' in v.keys():
                                           continue
                                       session = await click_by_key(
                                           session=session, host=host, key=k, client_id=session.vsess.client_id)
                                       if session:
                                           STATE = session.vsess.state
                                           break

           for key, value in STATE.items():
               if 'caption' in value.keys():
                   if VaadinActions.NEW_VARIANT in value['caption']:
                       if 'styles' in value.keys():
                           logger.info("STYLES")
                           continue
                       else:
                           session = await click_by_key(session, host=host, key=key, client_id=session.vsess.client_id)
                           print(session)'''

'''for client_id in range(COUNTER):
    session = await click_by_key(session=session, host=host, key=key, client_id=client_id)
    if session:
        print(session)
        continue
    else:
        print('ERROR')
    numb_variants = re.findall(r'(Вариант №\d+ - не завершен )', str(session))
    variants = await get_variants(session=qt_session, host=Host.QT_SPO)
    print(variants)
    if variants is None:
        logger.warning(f'IOM\nIom - {iom.id} no new variants for {account.login}')
        continue
    for variant in variants:
        if variant.code in numb_variants:
            print(variant.id)
            grade = await run_variant(
                pool, qt_session=qt_session, iom_id=iom.id, variant_id=variant.id)
            print(grade)
            #if grade == 5:
            #    GRADE -= 1
            #else:
            #    GRADE = 50
for key, value in STATE.items():
if 'caption' in value.keys():
if VaadinActions.JUMP in value['caption']:
session = await click_by_key(
session=session, host=host, key=key, client_id=session.vaadin.client_id+1)
print(session)
break

if session:
STATE = session.vaadin.state
for key, value in STATE.items():
if 'caption' in value.keys():
if VaadinActions.NEW_VARIANT in value['caption']:
if 'styles' in value.keys():
    logger.info("STYLES")
    continue
else:
    for client_id in range(COUNTER):
        session = await click_by_key(session=session, host=host, key=key,
                                     client_id=client_id+1)
        if session:
            print(session)
            continue
        else:
            print('ERROR')'''