from fastapi import APIRouter, Depends, HTTPException
from ..db import connection_db
from ..table import Questions, Ans, UserAns
from starlette import status
from sqlalchemy import func, select, or_, and_

router = APIRouter()


@router.post('/user')
def create_user_ans(userID: int, questionId: int, ansPosition: int = None, database=Depends(connection_db)):
    exists_question = database.query(Ans).filter(Ans.question_id == questionId)\
        .filter(or_(Ans.position == ansPosition, ansPosition is None)).first()
    if not exists_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='question or ans not found')

    query_max_id_user_ans = (
        database.query(func.max(UserAns.id).label("max_id"))
    )

    if query_max_id_user_ans.one().max_id is not None:
        max_id_user_ans = query_max_id_user_ans.one().max_id + 1
    else:
        max_id_user_ans = 1

    new_user_ans = UserAns(
        id=max_id_user_ans,
        user_id=userID,
        question_id=questionId,
        ans_position=ansPosition
    )

    database.add(new_user_ans)
    database.commit()

    return {
        'id': max_id_user_ans,
        'user_id': userID,
        'question_id': questionId,
        'ans_position': ansPosition
    }


@router.get('/user')
def get_current_unanswered_question(userID: int, database=Depends(connection_db)):
    exists_question = database.query(UserAns).filter(UserAns.user_id == userID).first()
    if not exists_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='user not found')

    query_questions = select(Questions)\
        .where(and_(UserAns.user_id == userID, UserAns.ans_position == None))\
        .where(Questions.id == UserAns.question_id) \
        .where(Questions.id == Ans.question_id)

    questions = database.execute(query_questions).first()
    database.commit()

    if questions is None:
        return {None}

    query_ans = select(Ans.position, Ans.text) \
        .where(and_(UserAns.user_id == userID, UserAns.ans_position == None)) \
        .where(Questions.id == UserAns.question_id) \
        .where(Questions.id == Ans.question_id) \
        .where(Questions.id == questions.Questions.id)

    ans = database.execute(query_ans).all()
    database.commit()

    return {
        "id": questions.Questions.id,
        'text': questions.Questions.text,
        'state': questions.Questions.state,
        'date': questions.Questions.date,
        'ansList': ans
    }
