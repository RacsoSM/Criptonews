from scripts import run_cycle as run_cycle_script


def test_main_initializes_db_then_runs_one_cycle(mocker):
    init_db_mock = mocker.patch("scripts.run_cycle.init_db")
    run_cycle_mock = mocker.patch("scripts.run_cycle.run_cycle")

    run_cycle_script.main()

    init_db_mock.assert_called_once()
    run_cycle_mock.assert_called_once()
