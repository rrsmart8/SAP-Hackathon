import sys
import datetime

def main():

    if len(sys.argv) < 6:
        print("[Erorr]: Wrong number of arguments!")
        return

    flight_number = sys.argv[1]
    load_f = sys.argv[2]
    load_b = sys.argv[3]
    load_p = sys.argv[4]
    load_e = sys.argv[5]

    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    print(f"Calculating strategy: F:{load_f}, B:{load_b}, P:{load_p}, E:{load_e}")

if __name__ == "__main__":
    main()