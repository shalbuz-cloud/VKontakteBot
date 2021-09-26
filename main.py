import os
import json

import requests
import youtube_dl


class DataBot:
    TOKEN = os.getenv('TOKEN')

    # FIXME При ненайденном сообществе парсится страница пользователя
    def __init__(self, group: str):
        self.group_id = group
        self.url = "https://api.vk.com/method/wall.get?domain={group}&count=40" \
                   "&access_token={token}&v=5.131".format(group=group, token=self.TOKEN)

    @staticmethod
    def __create_path(path: str):
        """
        Метод создает указанную директорию, если таковой нет.
        :param path:
        :return:
        """
        path = path.replace(' ', '_')
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def __json_save(data: list, file_name: str, path: str = ''):
        """
        Метод сохраняет данные в указанной директории в формате json.
        :param data: Сохраняемые данные
        :param file_name: Имя сохраняемого файла
        :param path: Расположение (путь) нового файла
        :return:
        """
        directory = os.path.join(path.replace(' ', '_'), file_name.replace(' ', '_'))
        with open('%s.json' % directory, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def download_img(self, url, file_name: str, path: str = ''):
        """
        Метод сохраняет изображение по ссылке в указанную директорию.
        :param url: URL ссылка на файл изображения.
        :param file_name: Имя сохраняемого файла.
        :param path: Путь (директория) сохраняемого файла.
        :return:
        """
        request = requests.get(url)
        path = os.path.join(path.replace(' ', '_'), 'media', 'img')

        self.__create_path(path)
        with open(os.path.join(path, file_name + '.jpg'), 'wb') as img_file:
            img_file.write(request.content)

    def download_video(self, url, file_name: str, path: str = '', max_duration=None):
        """
        Метод загружает видео по ссылке в указанную директорию. Если указан
        параметр max_duration, то будут загружены лишь те видео, которые не
        превышают это значение.
        :param url: URL ссылка на видео файл.
        :param file_name: Имя сохраняемого файла.
        :param path: Путь (директория) сохраняемого файла.
        :param max_duration: Максимальная длительность видео (в секундах).
        :return:
        """
        path = os.path.join(path.replace(' ', '_'), 'media', 'video')
        self.__create_path(path)

        try:
            ydl_options = {'outtmpl': '{}.%(ext)s'.format(os.path.join(path, file_name))}
            with youtube_dl.YoutubeDL(ydl_options) as ydl:
                video_info = ydl.extract_info(url, download=False)
                video_duration = video_info['duration']  # sec
                if max_duration is not None and video_duration > max_duration:
                    print("Видео длится дольше %s секунд, пропускаем его" % max_duration)
                else:
                    print("Видео длится %s секунд. Сохраняем видео..." % video_duration)
                    ydl.download([url])

        except Exception as ex:
            print("[ERROR] Не удалось скачать видео...| %s" % ex)

    def __get_post_data(self, post, file_name, save_media):
        """
        Функция получает медиа данные из поста и сохраняет их в директорию
        /имя_группы/media/img(video)/id_поста
        :param post: Объект обрабатываемого поста
        :param file_name: Имя сохраняемого файла (str)
        :param save_media: Сохранять полученные файлы или нет (bool)
        :return:
        """
        if post['type'] == "photo":
            post_photo = post['photo']['sizes'][-1]['url']
            print(post_photo)
            if save_media:
                self.download_img(post_photo, str(file_name), str(self.group_id))

        elif post['type'] == 'video':
            video_access_key = post['video']['access_key']
            video_post_id = post['video']['id']
            video_owner_id = post['video']['owner_id']

            video_get_url = "https://api.vk.com/method/video.get?videos=%s_%s_%s&access_token=%s" \
                            "&v=5.131" % (video_owner_id, video_post_id,
                                          video_access_key, self.TOKEN)

            video_data = requests.get(video_get_url).json()
            video_url = video_data['response']['items'][0]['player']
            print(video_url)

            if save_media:
                self.download_video(video_url, str(file_name), str(self.group_id))

    def get_wall_posts(self, save_media: bool = False):
        """
        Метод для получения и сохранения содержимого постов со стены
        сообщества.
        :param save_media: Нужно сохранять медия файлы или нет (True/False).
        :return:
        """

        try:
            data = requests.get(self.url).json()
            posts = data['response']['items']

            # Создаем папку, если таковой нет и сохраняем файл
            print("Сохраняем результат запроса в файл %s.json" % self.group_id)
            self.__create_path(self.group_id)
            self.__json_save(data, self.group_id, self.group_id)

            # Собираем id новых постов в список
            fresh_posts_id = [i['id'] for i in posts]

            """ Проверка, если файла не существует, значит это первый парсинг
            группы (отправляем все новые посты). Иначе начинаем проверку
            и отправляем только новые посты. """
            exists_posts_path = os.path.join(self.group_id,
                                             'exist_posts_' + self.group_id + '.txt')
            if not os.path.exists(exists_posts_path):
                print('Файла с ID постов не существует, создаем файл')
                with open(exists_posts_path, 'w') as file:
                    for item in fresh_posts_id:
                        file.write(str(item) + '\n')

                # Извлекаем данные из постов
                for post in posts:
                    post_id = post['id']
                    print("Отправляем пост с ID %s" % post_id)

                    try:
                        post = post.get('attachments')
                        if post is not None:
                            # Исключаем опросы из списка постов
                            post = list(filter(lambda k: k['type'] != 'poll', post))
                            # Обрабатываем одиночный пост
                            if len(post) == 1:
                                post = post[0]
                                self.__get_post_data(post, post_id, save_media)
                            # Обрабатываем мульти пост
                            else:
                                count = 0
                                for item in post:
                                    count += 1
                                    item_name = '%s_%s' % (post_id, count)
                                    self.__get_post_data(item, item_name, save_media)

                    except Exception as ex:
                        print("[ERROR] При сборе данных произошла ошибка. ID поста: %s | %s"
                              % (post_id, ex))

            else:
                print("Файл с ID постов найден, начинаем выборку свежих постов")

        except Exception as ex:
            print("[ERROR] При выполнении запроса произошла ошибка | %s" % ex)


def main():
    group_id = input('Введите id группы: ')
    vk_bot = DataBot(group_id)
    vk_bot.get_wall_posts()


if __name__ == '__main__':
    main()
