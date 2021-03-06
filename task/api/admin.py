from fastapi import APIRouter, Depends, HTTPException, Query
from ..db import connection_db
from ..models.admin import QuestionDto, QuestionState
from ..table import Questions, Ans, State, UserAns
from starlette import status
from datetime import date
from sqlalchemy import update, delete, func, select, and_, desc
from typing import Union

router = APIRouter()


@router.post('/admin')
def create_question(question: QuestionDto, database=Depends(connection_db)):
    exists_question = database.query(Questions.id).filter(Questions.text == question.text).one_or_none()
    if exists_question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Questions already exists')

    query_max_id_question = (
        database.query(func.max(Questions.id).label("max_id"))
    )

    if query_max_id_question.one().max_id is not None:
        max_id_question = query_max_id_question.one().max_id + 1
    else:
        max_id_question = 1

    new_question = Questions(
        id=max_id_question,
        text=question.text,
        state=question.state.value,
        date=date.today()
    )

    database.add(new_question)
    database.commit()

    query_max_id_ans = (
        database.query(func.max(Ans.id).label("max_id"))
    )

    if query_max_id_ans.one().max_id is not None:
        max_id_ans = query_max_id_ans.one().max_id + 1
    else:
        max_id_ans = 1

    for index, value in enumerate(question.ansList):
        new_ans = Ans(
            id=max_id_ans,
            text=value.text,
            position=index + 1,
            question_id=max_id_question
        )
        max_id_ans += 1

        database.add(new_ans)
        database.commit()

    return {
        'id': new_question.id,
        'text': new_question.text,
        'state': new_question.state,
        'ans': question.ansList,
        'date': new_question.date
    }


@router.put('/admin/setState')
def change_state(id: int, state: State, database=Depends(connection_db)):
    exists_question = database.query(Questions).filter(Questions.id == id).one_or_none()
    if not exists_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')

    update_question = (
        update(Questions).where(Questions.id == id).
            values(state=state.value)
    )

    database.execute(update_question)
    database.commit()

    return {"id": id, exists_question.text: state.value}


@router.get('/admin/questionById')
def get_question(id: int, database=Depends(connection_db)):
    exists_question = database.query(Questions).filter(Questions.id == id).one_or_none()
    if not exists_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')

    ans = database.query(Ans).filter(Ans.question_id == id).all()

    return {
        'id': exists_question.id,
        'data': exists_question.text,
        'state': exists_question.state,
        'date': exists_question.date,
        'ans': ans
    }


@router.put('/admin')
def change_question(id: int, question: QuestionDto, database=Depends(connection_db)):
    exists_question = database.query(Questions).filter(Questions.id == id).one_or_none()
    if not exists_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')
    if exists_question.text == question.text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Questions already exists')

    update_question = (
        update(Questions).where(Questions.id == id).
            values(
            text=question.text,
            state=question.state.value,
            date=date.today()
        )
    )

    database.execute(update_question)
    database.commit()

    delete_ans = (
        delete(Ans).where(Ans.question_id == id)
    )

    database.execute(delete_ans)
    database.commit()

    query_max_id_ans = (
        database.query(func.max(Ans.id).label("max_id"))
    )

    if query_max_id_ans.one().max_id is not None:
        max_id_ans = query_max_id_ans.one().max_id + 1
    else:
        max_id_ans = 1

    for index, value in enumerate(question.ansList):
        new_ans = Ans(
            id=max_id_ans,
            text=value.text,
            position=index,
            question_id=id
        )
        max_id_ans += 1

        database.add(new_ans)
        database.commit()

    return {
        'id': id,
        'text': question.text,
        'state': question.state,
        'ans': question.ansList,
        'date': date.today()
    }


@router.delete('/admin')
def delete_question(id: int, database=Depends(connection_db)):
    exists_question = database.query(Questions).filter(Questions.id == id).one_or_none()
    if not exists_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')

    delete_ans = (
        delete(Ans).where(Ans.question_id == id)
    )

    database.execute(delete_ans)
    database.commit()

    delete_user_ans = (
        delete(UserAns).where(UserAns.question_id == id)
    )

    database.execute(delete_user_ans)
    database.commit()

    delete_questions = (
        delete(Questions).where(Questions.id == id)
    )

    database.execute(delete_questions)
    database.commit()

    return {'delete': 'success'}


@router.get('/admin/statistic')
def get_statistic(id: int, database=Depends(connection_db)):
    exists_question = database.query(Questions).filter(Questions.id == id).one_or_none()
    if not exists_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Question not found')

    all_count_ans = (
        database.query(func.count(UserAns.ans_position).label("count")).filter(UserAns.question_id == id)
    )

    query = select(Ans.text, func.count(UserAns.ans_position).label("count")) \
        .where(UserAns.question_id == id) \
        .where(Questions.id == UserAns.question_id) \
        .where(Questions.id == Ans.question_id) \
        .where(Ans.position == UserAns.ans_position) \
        .group_by(Ans.text)

    query_question = database.execute(query).all()
    database.commit()

    return {
        'text': exists_question.text,
        'count': all_count_ans.one().count,
        'ansList': query_question
    }


@router.get('/admin')
def get_cropped_list_questions(
        search: str,
        state: QuestionState,
        page: Union[int, None] = Query(default=0),
        size: Union[int, None] = Query(default=20),
        database=Depends(connection_db)
):
    query_cropped_questions = database.query(Questions.id, Questions.text)\
        .where(and_(Questions.text.like(f'%{search}%'), Questions.state == state))\
        .order_by(desc(Questions.date))
    content = database.execute(query_cropped_questions).all()
    database.commit()

    query_count = database.query(func.count(Questions.id).label("count")) \
        .where(and_(Questions.text.like(f'%{search}%'), Questions.state == state))
    totalElements = database.execute(query_count).one()
    database.commit()

    if totalElements.count % size != 0:
        totalPages = int(totalElements.count / size) + 1
    else:
        totalPages = int(totalElements.count / size)

    return {
        'content': content[page*size:page*size+size],
        'totalElements': totalElements.count,
        'totalPages': totalPages
    }
