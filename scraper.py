from linkedin import Linkedin


def main():
    """
    to-do
    """
    # input_file_path = sys.argv[1]
    linkedin = Linkedin('vivek.anand@springboard.com', 'qwertyuiop@1')
    linkedin.scrape_student_info()


if __name__ == "__main__":
    main()
