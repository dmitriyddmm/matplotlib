import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (
    QWidget,
    QApplication,
    QBoxLayout,
    QComboBox,
    QListWidget,
    QAbstractItemView,
    QGridLayout,
    QGroupBox,
    QPushButton,
    QMessageBox
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

FILE_NAME = "data.xlsx"
data_file = pd.ExcelFile(FILE_NAME)
pd_sheets = {sheet: data_file.parse(sheet) for sheet in data_file.sheet_names}
np_sheets = [df.to_numpy() for df in pd_sheets.values()]
data = np.stack(np_sheets, axis=0)

FILE_NAME = "metadata.xlsx"
data_file = pd.ExcelFile(FILE_NAME)
pd_element_names = data_file.parse("Названия")
elements = {}
for element_name in pd_element_names.columns.values:
    elements[element_name] = {}
    elements[element_name]["Значения"] = [str(element) for element in pd_element_names[element_name].tolist()]
elements["Регионы"]["Типы диаграммы"] = ["График", "Столбчатая"]
elements["Годы"]["Типы диаграммы"] = ["Круговая"]
elements["Компании"]["Типы диаграммы"] = ["График", "Столбчатая"]


def get_names(type_):
    """
    Возвращает список названий в одном измерении
    :param type_: строка, "Регионы", "Компании", "Годы"
    :return: список
    """
    return elements[type_]["Значения"]


def transpose_as(data_, old_dimensions, new_dimensions):
    """
    Меняет оси массива в указанном порядке
    :param old_dimensions: список строк, названия измерений в порядке, в котором они во входном массиве
    :param data_: numpy-массив, объект изменения осей
    :param new_dimensions: список строк, названия измерений в порядке, в котором они будут в выходном массиве
    :return: numpy-массив
    """
    new_dimension_numbers = []
    for dimension in new_dimensions:
        new_dimension_numbers.append(list(old_dimensions).index(dimension))
    result = data_.transpose(new_dimension_numbers)
    return result


def get_elements(data_, type_, names):
    """
    Возвращает срез (массив, урезанный по указанным значениям верхней размерности), по каждому измерению может быть проведён только один раз
    :param data_: numpy-массив, объект среза
    :param type_: строка, тип элемента (регионы, компании, годы)
    :param names: список строк, значения верхней размерности, по которым проводится срез
    :return: numpy-массив
    """
    all_elements = elements[type_]["Значения"]
    element_numbers = [all_elements.index(element_name) for
                       element_name in
                       all_elements if
                       (element_name in names)]
    result = np.array([data_[element_number] for element_number in element_numbers])
    if len(result) == 1:
        result = result[0]
    return result


"""
перед каждым вырезом надо транспонировать массив так, чтобы на верхнюю размерность приходилось то, по чему будет сделан вырез
исключение - когда предыдущий вырез был сделан по 1 элементу, поскольку в этом случае вторая сверху размерность автоматически становится верхней
для построения графиков нужно, чтобы год был нижней размерностью,
поскольку каждый элемент верхней (второй) размерности должен содержать значения объекта для всех указанных лет
пример для выреза
  вход: "Москва", ["2010", "2011", "2012"], ["Сладкая жизнь", "Гранд-Альфа"]
  выход: [[33, 31, 57], [42, 89, 82]]
values = transpose_as(data, elements.keys(), ["Регионы", "Годы", "Компании"])
values = get_elements(values, "Регионы", ["Москва"])
values = get_elements(values, "Годы", ["2010", "2011", "2012"])
values = transpose_as(values, ["Годы", "Компании"], ["Компании", "Годы"])
values = get_elements(values, "Компании", ["Сладкая жизнь", "Гранд-Альфа"])
print(values)
"""


def create_gb_with_lo(name, direction, *elements_):
    """
    Создаёт GroupBox с обводкой, выровненный внутри при помощи Layout, и заполняет его элементами
    :param name: строка, название GroupBox (отображаемый текст)
    :param direction: QBoxLayout.Direction, направление выравнивания в Layout (по горизонтали/вертикали)
    :param elements_: список Widget/Layout, располагаемых внутри GroupBox
    :return: GroupBox
    """
    gb = QGroupBox(name)
    lo = QBoxLayout(direction)
    for element in elements_:
        if type(element) is QBoxLayout or type(element) is QGridLayout:
            lo.addLayout(element)
        else:
            lo.addWidget(element)
    gb.setLayout(lo)
    return gb


def create_lo(direction, *elements_):
    """
    Создаёт Layout без обводки и заполняет его элементами
    :param direction: QBoxLayout.Direction, направление выравнивания в Layout (по горизонтали/вертикали)
    :param elements_: список Widget/Layout, располагаемых внутри GroupBox
    :return: Layout
    """
    lo = QBoxLayout(direction)
    for element in elements_:
        if type(element) is QBoxLayout or type(element) is QGridLayout:
            lo.addLayout(element)
        else:
            lo.addWidget(element)
    return lo


def create_lb(items):
    """
    Создаёт список с множественным выбором ListWidget и заполняет его элементами
    :param items: список строк, текст элементов ListWidget
    :return: ListBox
    """
    lb = QListWidget()
    lb.addItems(items)
    lb.setSelectionMode(QAbstractItemView.ExtendedSelection)
    return lb


def create_cb(items):
    """
    Создаёт выпадающий список ComboBox
    :param items: список строк, текст элементов ComboBox
    :return: ComboBox
    """
    cb = QComboBox()
    cb.addItems(items)
    return cb


class MatplotlibWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.lo_mpl = None
        self.canvas = None
        self.figure = None
        self.gb_cut = None
        self.gb_diagram_type = None
        self.lb_elements_type_2 = None
        self.gb_elements_type_2 = None
        self.cb_diagram_type = None
        self.gb_elements_type_1 = None
        self.gb_dimension_names = None
        self.cb_dimension_names = None
        self.mpl = None
        self.lo_main = None
        self.pb_show = None
        self.lo_data = None
        self.gb_output_data = None
        self.gb_input_data = None
        self.gb_dimension = None
        self.gb_dimension_values = None
        self.cb_dimension_values = None
        self.lb_elements_type_1 = None
        self.create_window()

    def get_data_from_form(self):
        """
        Собирает данные с формы в переменную
        :return: словарь, собранные данные
        """

        data_from_form = {
            "Измерение": self.cb_dimension_names.currentText(),
            "Значение": self.cb_dimension_values.currentText(),
            "Тип диаграммы": self.cb_diagram_type.currentText(), "Отображаемые элементы": [
                {
                    "Название": "",
                    "Значения": []
                },
                {
                    "Название": "",
                    "Значения": []
                }
            ]
        }

        data_from_form["Отображаемые элементы"][0]["Название"] = self.gb_elements_type_1.title()
        data_from_form["Отображаемые элементы"][0]["Значения"] = [value.text() for value in
                                                                  self.lb_elements_type_1.selectedItems()]

        data_from_form["Отображаемые элементы"][1]["Название"] = self.gb_elements_type_2.title()
        values_ = [value.text() for value in self.lb_elements_type_2.selectedItems()]
        if data_from_form["Отображаемые элементы"][1]["Название"] == "Годы":
            values_ = sorted([int(value) for value in values_])
        data_from_form["Отображаемые элементы"][1]["Значения"] = values_

        return data_from_form

    def get_visualising_data(self, data_from_form):
        """
        Выбирает из всех данных те, которые нужно визуализировать, в соответствии с информацией, собранной с формы
        :return: None
        """

        visualising_data = {
            "Тип": data_from_form["Тип диаграммы"]
        }

        if visualising_data["Тип"] == "Круговая":
            if len(data_from_form["Отображаемые элементы"][0]["Значения"]) == 1:
                one = 0
            elif len(data_from_form["Отображаемые элементы"][1]["Значения"]) == 1:
                one = 1
            else:
                one = None
            visualising_data["Название"] = (data_from_form["Отображаемые элементы"][one]["Значения"][0] +
                                            ", " +
                                            data_from_form["Значение"] +
                                            " год")
            visualising_data["Метки"] = data_from_form["Отображаемые элементы"][not one]["Значения"]

            values = transpose_as(
                data,
                elements.keys(),
                [
                    "Годы",
                    data_from_form["Отображаемые элементы"][one]["Название"],
                    data_from_form["Отображаемые элементы"][not one]["Название"]
                ]
            )
            values = get_elements(
                values, "Годы",
                [data_from_form["Значение"]]
            )
            values = get_elements(
                values,
                data_from_form["Отображаемые элементы"][one]["Название"],
                data_from_form["Отображаемые элементы"][one]["Значения"]
            )
            values = get_elements(
                values,
                data_from_form["Отображаемые элементы"][not one]["Название"],
                data_from_form["Отображаемые элементы"][not one]["Значения"]
            )
            visualising_data["Значения"] = values.tolist()

        else:
            visualising_data["Название"] = data_from_form["Значение"]
            if data_from_form["Отображаемые элементы"][0]["Название"] == "Годы":
                years_number = 0
            else:
                years_number = 1
            visualising_data["Ось"] = {
                "Название": "Годы",
                "Значения": data_from_form["Отображаемые элементы"][years_number]["Значения"]
            }
            values = transpose_as(
                data,
                elements.keys(),
                [
                    data_from_form["Измерение"],
                    "Годы",
                    data_from_form["Отображаемые элементы"][not years_number]["Название"]
                ]
            )
            values = get_elements(
                values,
                data_from_form["Измерение"],
                [data_from_form["Значение"]]
            )
            data_from_form["Отображаемые элементы"][years_number]["Значения"] = [str(i) for i in data_from_form[
                "Отображаемые элементы"][years_number]["Значения"]]
            values = get_elements(
                values,
                "Годы",
                data_from_form["Отображаемые элементы"][years_number]["Значения"]
            )
            values = transpose_as(
                values,
                [
                    "Годы",
                    data_from_form["Отображаемые элементы"][not years_number]["Название"]
                ],
                [
                    data_from_form["Отображаемые элементы"][not years_number]["Название"],
                    "Годы"
                ]
            )
            values = get_elements(
                values,
                data_from_form["Отображаемые элементы"][not years_number]["Название"],
                data_from_form["Отображаемые элементы"][not years_number]["Значения"]
            )
            visualising_data["Значения"] = []
            for i, year in enumerate(data_from_form["Отображаемые элементы"][abs(years_number - 1)]["Значения"]):
                visualising_data["Значения"].append({"Название": year, "Значения": values[i].tolist()})

        return visualising_data

    def visualise(self, visualising_data):
        self.mpl.figure.clear()
        ax = self.mpl.figure.add_subplot(111)
        ax.set_title(visualising_data["Название"])

        if visualising_data["Тип"] == "Круговая":
            ax.pie(visualising_data["Значения"], labels=visualising_data["Метки"], autopct='%1.1f%%', startangle=90)
            ax.axis('equal')

        elif visualising_data["Тип"] == "График":
            x = [str(i) for i in visualising_data["Ось"]["Значения"]]
            for element in visualising_data["Значения"]:
                y = element["Значения"]
                ax.plot(x, y)

        elif visualising_data["Тип"] == "Столбчатая":
            years = visualising_data["Ось"]["Значения"]
            x = np.arange(len(years))
            elements_count = len(visualising_data["Значения"])
            column_width = 1 / (elements_count * 1.5)
            widths = list(range(-elements_count + 1, elements_count - 1 + 2, 2))
            widths = [0.5 * i for i in widths]
            for i, width in enumerate(widths):
                ax.bar(x + column_width * width, visualising_data["Значения"][i]["Значения"], column_width,
                       label=visualising_data["Значения"][i]["Название"])
            ax.set_xticks(x)
            ax.set_xticklabels(years)
            ax.legend()

        self.mpl.canvas.draw()

    def pb_clicked(self):
        """
        Событие клика по кнопке
        :return:
        """
        try:
            data_from_form = self.get_data_from_form()
            visualising_data = self.get_visualising_data(data_from_form)
            self.visualise(visualising_data)
        except:
            mb = QMessageBox()
            mb.setIcon(QMessageBox.Critical)
            mb.setText("Неверная размерность указанных данных для выбранного типа диаграммы!")
            mb.setWindowTitle("Ошибка")
            mb.setStandardButtons(QMessageBox.Ok)
            return mb.exec()

    def cb_dimension_names_changed(self):
        """
        Событие изменения измерения: меняются все списки и выпадающие списки
        :return: None
        """

        self.cb_dimension_values.clear()
        self.cb_dimension_values.addItems(elements[self.cb_dimension_names.currentText()]["Значения"])

        self.cb_diagram_type.clear()
        self.cb_diagram_type.addItems(elements[self.cb_dimension_names.currentText()]["Типы диаграммы"])

        visual_types = list(elements.keys())
        visual_types.remove(self.cb_dimension_names.currentText())

        self.lb_elements_type_1.clear()
        self.lb_elements_type_1.addItems(elements[visual_types[0]]["Значения"])
        self.lb_elements_type_1.setCurrentItem(self.lb_elements_type_1.item(0))
        self.gb_elements_type_1.setTitle(visual_types[0])

        self.lb_elements_type_2.clear()
        self.lb_elements_type_2.addItems(elements[visual_types[1]]["Значения"])
        self.lb_elements_type_2.setCurrentItem(self.lb_elements_type_2.item(0))
        self.gb_elements_type_2.setTitle(visual_types[1])

    def create_cut_block(self):
        """
        Создаёт блок среза
        :return: None
        """

        self.cb_dimension_names = create_cb(elements.keys())
        self.cb_dimension_names.currentIndexChanged.connect(self.cb_dimension_names_changed)
        self.gb_dimension_names = create_gb_with_lo(
            "Измерение",
            QBoxLayout.TopToBottom,
            self.cb_dimension_names
        )

        self.cb_dimension_values = create_cb(elements[self.cb_dimension_names.currentText()]["Значения"])
        self.gb_dimension_values = create_gb_with_lo(
            "Значение",
            QBoxLayout.TopToBottom,
            self.cb_dimension_values
        )

        self.cb_diagram_type = create_cb(elements[self.cb_dimension_names.currentText()]["Типы диаграммы"])
        self.gb_diagram_type = create_gb_with_lo(
            "Тип диаграммы",
            QBoxLayout.TopToBottom,
            self.cb_diagram_type
        )

        self.gb_cut = create_gb_with_lo(
            "Срез",
            QBoxLayout.TopToBottom,
            self.gb_dimension_names,
            self.gb_dimension_values,
            self.gb_diagram_type
        )

    def create_visual_elements_block(self):
        """
        Создаёт блок отображаемых элементов
        :return: None
        """

        self.lb_elements_type_1 = create_lb(elements[list(elements.keys())[1]]["Значения"])
        self.lb_elements_type_1.setCurrentItem(self.lb_elements_type_1.item(0))
        self.gb_elements_type_1 = create_gb_with_lo(
            list(elements.keys())[1],
            QBoxLayout.TopToBottom,
            self.lb_elements_type_1
        )

        self.lb_elements_type_2 = create_lb(elements[list(elements.keys())[2]]["Значения"])
        self.lb_elements_type_2.setCurrentItem(self.lb_elements_type_2.item(0))
        self.gb_elements_type_2 = create_gb_with_lo(
            list(elements.keys())[2],
            QBoxLayout.TopToBottom,
            self.lb_elements_type_2
        )

        self.gb_dimension = create_gb_with_lo(
            "Отображаемые элементы",
            QBoxLayout.TopToBottom,
            self.gb_elements_type_1,
            self.gb_elements_type_2
        )

    def create_input_data_block(self):
        """
        Создаёт блок входных данных
        :return: None
        """
        self.gb_input_data = create_gb_with_lo(
            "Входные данные",
            QBoxLayout.TopToBottom,
            self.gb_cut,
            self.gb_dimension
        )
        self.gb_input_data.setFixedWidth(300)

    def create_output_data_block(self):
        """
        Создаёт блок выходных данных
        :return: None
        """
        self.mpl = MatplotlibWidget()
        self.lo_mpl = create_lo(QBoxLayout.TopToBottom, self.mpl.canvas)

        self.gb_output_data = create_gb_with_lo(
            "Выходные данные",
            QBoxLayout.TopToBottom,
            self.lo_mpl
        )
        self.gb_output_data.setFixedWidth(800)

    def create_data_block(self):
        """
        Создаёт блок данных
        :return: None
        """
        self.lo_data = create_lo(
            QBoxLayout.LeftToRight,
            self.gb_input_data,
            self.gb_output_data
        )

    def create_main_block(self):
        """
        Создаёт основной блок
        :return: None
        """
        self.pb_show = QPushButton("Показать")
        self.pb_show.setFixedWidth(300)
        self.pb_show.clicked.connect(self.pb_clicked)
        self.lo_main = create_lo(
            QBoxLayout.TopToBottom,
            self.lo_data,
            self.pb_show
        )
        self.setLayout(self.lo_main)

    def create_window(self):
        """
        Создаёт окно
        :return: None
        """
        self.setWindowTitle("Сравнение прибыли компаний")
        self.move(100, 20)
        self.create_cut_block()
        self.create_visual_elements_block()
        self.create_input_data_block()
        self.create_output_data_block()
        self.create_data_block()
        self.create_main_block()


app = QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
sys.exit(app.exec_())
