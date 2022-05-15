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

    def __init__(self, master, base_id, ss_nr):

        self.master = master

        self.stage_list = None
        self.absolute_list = None
        self.ss_id = base_id + ss_nr

        self.valid = True

        self.generate_results()

    def generate_results(self):
        r = requests.get('https://www.autosport.ee/xml/results/race_res_' + str(self.ss_id) + '_abs.xml')
        if r.status_code != 200:
            self.valid = False
        else:
            self.absolute_list = xmltodict.parse(r.text)["race"]["ss_res_list"]["ss_res"]
        r = requests.get('https://www.autosport.ee/xml/results/race_res_' + str(self.ss_id) + '_ss.xml')
        if r.status_code != 200:
            self.valid = False
        else:
            self.stage_list = xmltodict.parse(r.text)["race"]["ss_res_list"]["ss_res"]

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
        self.api.add_url_rule('/rally/SS<req_id>/abs', 'SS_abs_res', self.get_overall_abs)
        self.api.add_url_rule('/rally/reset', 'Reset lists in case of problems', self.clear_finishers_list)

    def clear_finishers_list(self):
        self.stage_finishers_list = {}

        return Response("Finishers list cleared")

    def get_overall_last_results(self, req_id):
        print("Last finisher absolute info request")
        stage_id = int(req_id)
        results = StageResults(self, self.base_id, stage_id)
        if not results.valid:
            placeholder = ET.parse('NoResults_last.xml')
            return Response(ET.tostring(placeholder.getroot()), mimetype='text/xml')

        last_finisher_nr = results.get_last_finisher_number(stage_id)
        try:
            xml = results.create_last_finisher_xml(last_finisher_nr)
            print("Last finisher data generated for nr.{}".format(last_finisher_nr))
            return Response(xml, mimetype='text/xml')
        except IndexError:
            print("No results yet")
            return Response("No results yet")

    def get_overall_abs(self, req_id):
        print("SS{} absolute TOP10 request".format(int(req_id)))
        stage_id = int(req_id)
        results = StageResults(self, self.base_id, stage_id)
        if not results.valid:
            placeholder = ET.parse('NoResults_abs.xml')
            return Response(ET.tostring(placeholder.getroot()), mimetype='text/xml')
        try:
            xml = results.create_abs_result_xml()
            return Response(xml, mimetype='text/xml')
        except IndexError:
            print("No results yet")
            return Response("No results yet")

    def get_overall_class_result(self, req_id):
        print("Last finisher absolute class info request")
        stage_id = int(req_id)
        results = StageResults(self, self.base_id, stage_id)
        if not results.valid:
            placeholder = ET.parse('NoResults_class.xml')
            return Response(ET.tostring(placeholder.getroot()), mimetype='text/xml')

        last_finisher_nr = results.get_last_finisher_number(stage_id)
        try:
            xml = results.create_class_result_xml(last_finisher_nr)
            print("Last finisher class data generated for nr.{}".format(last_finisher_nr))
            return Response(xml, mimetype='text/xml')
        except IndexError:
            print("No results yet")
            return Response("No results yet")


if __name__ == '__main__':
    bb = BBRallyResults(1154)
    bb.api.run(host='0.0.0.0', port=4455)
