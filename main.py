import os
import json

import requests


class DataBot:
    TOKEN = os.getenv('TOKEN')

    def __init__(self, group: str):
        self.group_id = group
        self.url = "https://api.vk.com/method/wall.get?domain={group}&count=40" \
                   "&access_token={token}&v=5.131".format(group=group, token=self.TOKEN)

    @staticmethod
    def __get_data(url: str):
        return requests.get(url)

    @staticmethod
    def __create_path(path: str):
        path = path.replace(' ', '_')
        if not os.path.exists(path):
            os.mkdir(path)

    @staticmethod
    def __json_save(data: list, file_name: str, path: str = ''):
        directory = os.path.join(path.replace(' ', '_'), file_name.replace(' ', '_'))
        with open('%s.json' % directory, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def get_wall_posts(self):

        try:
            data = self.__get_data(self.url).json()
            posts = data['response']['items']

            # Создаем папку, если таковой нет и сохраняем файл
            print("Сохраняем результат запроса в файл %s.json" % group_id)
            self.__create_path(self.group_id)
            self.__json_save(data, self.group_id, self.group_id)

            # Собираем id новых постов в список
            fresh_posts_id = [i['id'] for i in posts]

            """ Проверка, если файла не существует, значит это первый парсинг
            группы (отправляем все новые посты). Иначе начинаем проверку
            и отправляем только новые посты. """
            if not os.path.exists('{0}/exist_posts_{0}.txt'.format(group_id)):
                print('Файла с ID постов не существует, создаем файл')
                with open('{0}/exist_posts_{0}.txt'.format(group_id), 'w') as file:
                    for item in fresh_posts_id:
                        file.write(str(item) + '\n')

                # Извлекаем данные из постов
                for post in posts:
                    post_id = post['id']
                    print("Отправляем пост с ID %s" % post_id)

                    try:
                        post = post.get('attachments')
                        if post is not None:
                            post = post[0]

                            if post['type'] == "photo":
                                post_photo = post['photo']['sizes'][-1]['url']
                                print(post_photo)
                            elif post['type'] == 'video':
                                video_access_key = post['video']['access_key']
                                video_post_id = post['video']['id']
                                video_owner_id = post['video']['owner_id']

                                video_get_url = "https://api.vk.com/method/video.get?videos=%s_" \
                                                "%s_%s&access_token=%s&v=5.131" % (
                                                    video_owner_id, video_post_id,
                                                    video_access_key, self.TOKEN)

                                video_data = requests.get(video_get_url).json()
                                video_url = video_data['response']['items'][0]['player']
                                print(video_url)

                            else:
                                continue

                    except Exception as ex:
                        print("[ERROR] При сборе данных произошла ошибка. ID поста: %s | %s"
                              % (post_id, ex))

            else:
                print("Файл с ID постов найден, начинаем выборку свежих постов")

        except Exception as ex:
            print("[ERROR] При выполнении запроса произошла ошибка | %s" % ex)


if __name__ == '__main__':
    group_id = input('Введите id группы: ')
    vkBot = DataBot(group_id)
    vkBot.get_wall_posts()
