from flask import Flask, Response
import xml.etree.ElementTree as ET
import requests
import xmltodict


def create_pos_xml(parent, pos, table_name, table):
    # numbers in list start from 0, so we subtract for 1 to match
    pos_in_list = pos - 1
    xml_table = ET.SubElement(parent, table_name)
    ET.SubElement(xml_table, 'pos').text = str(pos)
    ET.SubElement(xml_table, 'number').text = table[pos_in_list]["car_no"]
    ET.SubElement(xml_table, 'fullname').text = table[pos_in_list]["driver_firstname"] + " " + \
                                                table[pos_in_list]["driver_lastname"]
    ET.SubElement(xml_table, 'lastname').text = table[pos_in_list]["driver_lastname"]
    ET.SubElement(xml_table, 'firstname').text = table[pos_in_list]["driver_firstname"]
    ET.SubElement(xml_table, 'participants').text = table[pos_in_list]["driver_firstname"] + " " + \
                                                    table[pos_in_list]["driver_lastname"] + " / " + \
                                                    table[pos_in_list]["codriver_firstname"] + " " + \
                                                    table[pos_in_list]["codriver_lastname"]
    if pos == 1:
        ET.SubElement(xml_table, 'time').text = table[pos_in_list]["time_formatted"]
    else:
        time_loss_raw = float(table[pos_in_list]["time_raw"]) - float(table[0]["time_raw"])
        time_loss = int(time_loss_raw * 100)
        ET.SubElement(xml_table, 'time').text = '+{}:{}.{}'.format(int(time_loss / 6000),
                                                                   int((time_loss % 6000) / 100),
                                                                   int(time_loss % 100))


def create_empty_pos_xml(parent, table_name):
    xml_table = ET.SubElement(parent, table_name)
    ET.SubElement(xml_table, 'pos').text = "-"
    ET.SubElement(xml_table, 'number').text = "-"
    ET.SubElement(xml_table, 'fullname').text = "-"
    ET.SubElement(xml_table, 'lastname').text = "-"
    ET.SubElement(xml_table, 'firstname').text = "-"
    ET.SubElement(xml_table, 'participants').text = "-"
    ET.SubElement(xml_table, 'time').text = "-"


class StageResults:

    def __init__(self, master, stage_list, absolute_list):

        self.master = master

        self.stage_list = stage_list
        self.absolute_list = absolute_list

    def get_last_finisher_number(self, stage_id):
        try:
            stage_finisher_list = self.master.stage_finishers_list[stage_id]
        except KeyError:
            stage_finisher_list = []
        for result in self.stage_list:
            start_number = int(result["car_no"])
            if start_number not in stage_finisher_list:
                stage_finisher_list.append(start_number)

        last_finisher_nr = stage_finisher_list[-1]
        self.master.stage_finishers_list[stage_id] = stage_finisher_list

        return last_finisher_nr

    def create_last_finisher_xml(self, last_finisher_nr):
        last_finisher = list(filter(lambda car: car["car_no"] == str(last_finisher_nr), self.stage_list))[0]
        best_time = float(self.stage_list[0]["time_raw"])
        second_best = float(self.stage_list[1]["time_raw"])

        a = ET.Element('rally')
        b = ET.SubElement(a, 'latest')
        # ET.SubElement(b, 'position').text = last_finisher["pos"]
        ET.SubElement(b, 'position').text = str(self.stage_list.index(last_finisher) + 1)
        ET.SubElement(b, 'start-number').text = last_finisher["car_no"]
        ET.SubElement(b, 'drivers').text = '{} - {}'.format(last_finisher["driver_lastname"],
                                                            last_finisher["codriver_lastname"])
        ET.SubElement(b, 'driver').text = '{}. {}'.format(last_finisher["driver_firstname"][0],
                                                          last_finisher["driver_lastname"])
        ET.SubElement(b, 'driver-first').text = '{}'.format(last_finisher["driver_firstname"])
        ET.SubElement(b, 'driver-last').text = '{}'.format(last_finisher["driver_lastname"])
        ET.SubElement(b, 'co-driver').text = '{}. {}'.format(last_finisher["codriver_firstname"][0],
                                                             last_finisher["codriver_lastname"])
        ET.SubElement(b, 'car').text = '{} {}'.format(last_finisher["car_brand"], last_finisher["car_model"])
        ET.SubElement(b, 'time').text = last_finisher["time_formatted"]
        loss = ET.SubElement(b, 'loss')

        if float(last_finisher["time_raw"]) != best_time:
            time_loss_raw = float(last_finisher["time_raw"]) - best_time
            time_loss = int(time_loss_raw * 100)
            loss.text = '+{}:{}.{}'.format(int(time_loss / 6000), int((time_loss % 6000) / 100), int(time_loss % 100))
        else:
            time_win_raw = second_best - float(last_finisher["time_raw"])
            time_win = int(time_win_raw * 100)
            loss.text = '-{}:{}.{}'.format(int(time_win / 6000), int((time_win % 6000) / 100), int(time_win % 100))

        return ET.tostring(a)

    def create_class_result_xml(self, last_finisher_nr):
        last_finisher = list(filter(lambda car: car["car_no"] == str(last_finisher_nr), self.absolute_list))[0]
        abs_results = list(filter(lambda car: car["class_id"] == last_finisher["class_id"], self.absolute_list))
        stage_results = list(filter(lambda car: car["class_id"] == last_finisher["class_id"], self.stage_list))

        last_finisher_pos = abs_results.index(last_finisher) + 1
        res_list = abs_results
        class_fin_on_ss = len(stage_results)

        a = ET.Element('rally')
        comp_class = ET.SubElement(a, 'class')
        ET.SubElement(comp_class, 'class_name').text = last_finisher["class_name"]

        if class_fin_on_ss < 4 or last_finisher_pos < 3:
            res_cnt = class_fin_on_ss + 1
            print("res count {}".format(res_cnt))
            if res_cnt > 3:
                res_cnt = 3
            for i in range(1, res_cnt + 1):
                create_pos_xml(comp_class, i, 'class_dr', res_list)
            if res_cnt < 3:
                empty_values = 3 - res_cnt
                for i in range(empty_values):
                    create_empty_pos_xml(comp_class, 'class_dr')
        else:
            if last_finisher_pos == class_fin_on_ss:
                create_pos_xml(comp_class, last_finisher_pos - 2, 'class_dr', res_list)
                create_pos_xml(comp_class, last_finisher_pos - 1, 'class_dr', res_list)
                create_pos_xml(comp_class, last_finisher_pos, 'class_dr', res_list)
            else:
                create_pos_xml(comp_class, last_finisher_pos - 1, 'class_dr', res_list)
                create_pos_xml(comp_class, last_finisher_pos, 'class_dr', res_list)
                create_pos_xml(comp_class, last_finisher_pos + 1, 'class_dr', res_list)

        return ET.tostring(a)

    def create_abs_result_xml(self):

        res_list = self.absolute_list

        a = ET.Element('rally')
        b = ET.SubElement(a, 'absolute')
        for i in range(1, 11):
            create_pos_xml(b, i, 'driver', res_list)

        return ET.tostring(a)


class BBRallyResults:

    def __init__(self, base_stage_id):
        self.api = Flask("Baltic Broadcasting")

        self.base_id = base_stage_id

        self.stage_finishers_list = {}

        self.api.add_url_rule('/rally/SS<req_id>', 'SS_last_finisher', self.get_overall_last_results)
        self.api.add_url_rule('/rally/SS<req_id>/class', 'SS_last_finisher_class', self.get_overall_class_result)
        self.api.add_url_rule('/rally/SS<req_id>/abs', 'SS_abs_res', self.get_overall_abs_top5)
        self.api.add_url_rule('/rally/reset', 'Reset lists in case of problems', self.clear_finishers_list)

    def clear_finishers_list(self):
        self.stage_finishers_list = {}

        return Response("Finishers list cleared")

    def get_overall_last_results(self, req_id):
        print("Last finisher absolute info request")
        stage_id = int(req_id)
        results = self.generate_results(stage_id)
        last_finisher_nr = results.get_last_finisher_number(stage_id)
        try:
            xml = results.create_last_finisher_xml(last_finisher_nr)
            print("Last finisher data generated for nr.{}".format(last_finisher_nr))
            return Response(xml, mimetype='text/xml')
        except IndexError:
            print("No results yet")
            return Response("No results yet")

    def get_overall_abs_top5(self, req_id):
        print("SS{} absolute TOP5 request".format(int(req_id)))
        stage_id = int(req_id)
        results = self.generate_results(stage_id)
        try:
            xml = results.create_abs_result_xml()
            return Response(xml, mimetype='text/xml')
        except IndexError:
            print("No results yet")
            return Response("No results yet")

    def get_overall_class_result(self, req_id):
        print("Last finisher absolute class info request")
        stage_id = int(req_id)
        results = self.generate_results(stage_id)
        last_finisher_nr = results.get_last_finisher_number(stage_id)
        try:
            xml = results.create_class_result_xml(last_finisher_nr)
            print("Last finisher class data generated for nr.{}".format(last_finisher_nr))
            return Response(xml, mimetype='text/xml')
        except IndexError:
            print("No results yet")
            return Response("No results yet")

    def generate_results(self, stage_id):
        r = requests.get('https://www.autosport.ee/xml/results/race_res_' + str(self.base_id + stage_id) + '_abs.xml')
        absolute_list = xmltodict.parse(r.text)["race"]["ss_res_list"]["ss_res"]
        r = requests.get('https://www.autosport.ee/xml/results/race_res_' + str(self.base_id + stage_id) + '_ss.xml')
        stage_list = xmltodict.parse(r.text)["race"]["ss_res_list"]["ss_res"]

        return StageResults(self, stage_list, absolute_list)


'''
@api.route('/rally/SS<id>', methods=['GET'])
def get_SS_last_result(id):
    stage_id = int(id)
    r = requests.get('http://www.autosport.ee/xml/results/race_res_'+str(base_ss_id+stage_id)+'_abs.xml')
    absolute = ET.fromstring(r.text)
    r = requests.get('http://www.autosport.ee/xml/results/race_res_'+str(base_ss_id+stage_id)+'_ss.xml')
    stage = ET.fromstring(r.text)
    stage_list = xmltodict.parse(r.text)["race"]["ss_res_list"]["ss_res"]
    SS_last_finisher[id] = get_last_finisher_number(stage, id)
    finisher = list(filter(lambda car: car["car_no"] == str(SS_last_finisher[id]), stage_list))
    print("FILTER:")
    print(finisher)
    print('last finisher {}'.format(SS_last_finisher[id]))
    last_finisher = get_last_finisher(absolute, SS_last_finisher[id])
    xml = create_last_finisher_xml(absolute, last_finisher)
    return Response(xml, mimetype='text/xml')


@api.route('/rally/SS<id>/class', methods=['GET'])
def get_SS_class_result(id):
    print("class results")
    stage_id = int(id)
    r = requests.get('http://www.autosport.ee/xml/results/race_res_'+str(base_ss_id+stage_id)+'_abs.xml')
    absolute_list = xmltodict.parse(r.text)["race"]["ss_res_list"]["ss_res"]
    r = requests.get('http://www.autosport.ee/xml/results/race_res_'+str(base_ss_id+stage_id)+'_ss.xml')
    stage = ET.fromstring(r.text)
    SS_last_finisher[id] = get_last_finisher_number(stage, id)
    finisher = list(filter(lambda car: car["car_no"] == str(SS_last_finisher[id]), absolute_list))[0]
    class_results_list = list(filter(lambda car: car["class_id"] == finisher["class_id"], absolute_list))
    xml = create_class_result_xml(class_results_list, finisher)
    return Response(xml, mimetype='text/xml')


def create_class_result_xml(class_results, last_finisher):

    if last_finisher is None:
        return 'no results yet'

    finishers_count = len(class_results)
    last_finisher_pos = class_results.index(last_finisher)
    print("finisher cnt " + str(finishers_count))
    print("last finisher " + str(last_finisher_pos))

    a = ET.Element('rally')
    comp_class = ET.SubElement(a, 'class')
    ET.SubElement(comp_class, 'class_name').text = last_finisher["class_name"]
    create_pos_xml(comp_class, class_results, 1, 'first')
    create_pos_xml(comp_class, class_results, last_finisher_pos - 1, 'previous')
    create_pos_xml(comp_class, class_results, last_finisher_pos, 'finisher')
    create_pos_xml(comp_class, class_results, last_finisher_pos + 1, 'next')

    return ET.tostring(a)


def create_pos_xml(parent, class_results, pos, table_name):
    # numbers in list start from 0, so we subtract for 1 to match
    pos_in_list = pos - 1
    table = ET.SubElement(parent, table_name)
    ET.SubElement(table, 'pos').text = str(pos)
    ET.SubElement(table, 'name').text = class_results[pos_in_list]["driver_firstname"] + " " + class_results[pos_in_list]["driver_lastname"]
    if pos == 1:
        ET.SubElement(table, 'time').text = class_results[pos_in_list]["time_formatted"]
    else:
        time_loss_raw = float(class_results[pos_in_list]["time_raw"]) - float(class_results[0]["time_raw"])
        time_loss = int(time_loss_raw * 100)
        ET.SubElement(table, 'time').text = '+{}:{}.{}'.format(int(time_loss / 6000), int((time_loss % 6000) / 100), int(time_loss % 100))


def get_last_finisher_number(res_obj, stage_id):
    try:
        stage_finisher_list = SS_finisher_list[stage_id]
    except KeyError:
        stage_finisher_list = []
    for result in res_obj[0]:
        start_number = int(result[2].text)
        if start_number not in stage_finisher_list:
            stage_finisher_list.append(start_number)

    last_finisher_nr = stage_finisher_list[-1]
    SS_finisher_list[stage_id] = stage_finisher_list

    return last_finisher_nr


def get_last_finisher(res_obj, last_nr):

    last_finisher = None

    for result in res_obj[0]:
        start_number = int(result[2].text)
        if start_number == last_nr:
            last_finisher = result
            print('got last finisher from absolute')
            break

    return last_finisher


def get_position_time(res_obj, pos):

    best_time = float(res_obj[0][pos][12].text)
    print('pos {} nr {}'.format(pos + 1, res_obj[0][pos][2].text))
    print('pos {} time {}'.format(pos + 1, best_time))

    return best_time


def create_last_finisher_xml(res_obj, last_finisher):

    if last_finisher is None:
        return 'no results yet'

    best_time = get_position_time(res_obj, 0)
    second_best = get_position_time(res_obj, 1)

    print('best time {}'.format(best_time))
    print('second best time {}'.format(best_time))

    a = ET.Element('rally')
    b = ET.SubElement(a, 'latest')
    position = ET.SubElement(b, 'position')
    start_number = ET.SubElement(b, 'start-number')
    drivers = ET.SubElement(b, 'drivers')
    driver = ET.SubElement(b, 'driver')
    co_driver = ET.SubElement(b, 'co-driver')
    car = ET.SubElement(b, 'car')
    time = ET.SubElement(b, 'time')
    loss = ET.SubElement(b, 'loss')

    position.text = last_finisher[0].text
    start_number.text = last_finisher[2].text
    drivers.text = '{} - {}'.format(last_finisher[4].text, last_finisher[6].text)
    driver.text = '{}. {}'.format(last_finisher[3].text[0], last_finisher[4].text)
    co_driver.text = '{}. {}'.format(last_finisher[5].text[0], last_finisher[6].text)
    car.text = '{} {}'.format(last_finisher[7].text, last_finisher[8].text)
    time.text = last_finisher[13].text

    if float(last_finisher[12].text) != best_time:
        time_loss_raw = float(last_finisher[12].text) - best_time
        time_loss = int(time_loss_raw*100)
        loss.text = '+{}:{}.{}'.format(int(time_loss/6000), int((time_loss % 6000) / 100), int(time_loss % 100))
    else:
        time_win_raw = second_best - float(last_finisher[12].text)
        time_win = int(time_win_raw * 100)
        loss.text = '-{}:{}.{}'.format(int(time_win / 6000), int((time_win % 6000) / 100), int(time_win % 100))

    return ET.tostring(a)
'''

if __name__ == '__main__':
    bb = BBRallyResults(1154)
    bb.api.run(host='0.0.0.0', port=4455)
